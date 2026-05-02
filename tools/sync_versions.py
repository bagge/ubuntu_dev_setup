#!/usr/bin/env python3
"""Report and update pinned tool versions used by the playbooks."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
GROUP_VARS = REPO_ROOT / "group_vars" / "all"
TIMEOUT_SECONDS = 20


@dataclass(frozen=True)
class Source:
    name: str
    variable: str
    provider: str
    repo: str | None = None
    tag_prefix: str = ""
    assets: tuple[str, ...] = ()
    note: str = ""


SOURCES: tuple[Source, ...] = (
    Source("Bash-it", "bash_it_version", "github", "Bash-it/bash-it", "v"),
    Source(
        "Bazel buildtools",
        "bazel_buildtools_version",
        "github",
        "bazelbuild/buildtools",
        "v",
        (
            "buildifier-linux-amd64",
            "buildifier-darwin-arm64",
            "buildozer-linux-amd64",
            "buildozer-darwin-arm64",
            "unused_deps-linux-amd64",
            "unused_deps-darwin-arm64",
        ),
    ),
    Source(
        "Bazelisk",
        "bazelisk_version",
        "github",
        "bazelbuild/bazelisk",
        "v",
        ("bazelisk-linux-amd64", "bazelisk-darwin-arm64"),
    ),
    Source("fzf", "fzf_version", "github", "junegunn/fzf", "v"),
    Source(
        "glow",
        "glow_version",
        "github",
        "charmbracelet/glow",
        "v",
        ("glow_{version}_amd64.deb",),
    ),
    Source("Go", "golang_version", "go"),
    Source(
        "kitty",
        "kitty_version",
        "github",
        "kovidgoyal/kitty",
        "v",
        ("kitty-{version}-x86_64.txz",),
    ),
    Source(
        "mdcat",
        "mdcat_version",
        "github",
        "swsnr/mdcat",
        "mdcat-",
        ("mdcat-{version}-x86_64-unknown-linux-gnu.tar.gz",),
        "Ubuntu-only in this playbook.",
    ),
    Source(
        "Nerd Fonts",
        "nerd_fonts_version",
        "github",
        "ryanoasis/nerd-fonts",
        "v",
        ("Hack.zip",),
    ),
    Source("Node.js LTS major", "node_major_version", "node_lts_major"),
    Source("nvm", "nvm_version", "github", "nvm-sh/nvm", "v"),
    Source(
        "Neovim",
        "nvim_version",
        "github",
        "neovim/neovim",
        "v",
        ("nvim-linux-x86_64.tar.gz", "nvim-macos-arm64.tar.gz"),
    ),
    Source(
        "toprepo",
        "toprepo_version",
        "github",
        "meroton/git-toprepo",
        "",
        ("git-toprepo-{version}-linux-x86_64",),
    ),
    Source(
        "Omnissa Horizon Client",
        "horizon_deb",
        "manual",
        note="Vendor download pages do not expose a stable version API; update horizon_url and horizon_deb manually.",
    ),
    Source(
        "Omnissa Horizon Client URL",
        "horizon_url",
        "manual",
        note="Vendor download pages do not expose a stable version API; update horizon_url and horizon_deb manually.",
    ),
)


@dataclass(frozen=True)
class Result:
    source: Source
    current: str
    latest: str | None
    status: str
    note: str = ""

    @property
    def is_update(self) -> bool:
        return self.status == "update"


class VersionSyncError(RuntimeError):
    pass


class BlockedUpdateError(VersionSyncError):
    pass


def fetch_json(url: str) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ubuntu-dev-setup-version-sync",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def load_vars(path: Path = GROUP_VARS) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", line)
        if match:
            values[match.group(1)] = match.group(2).strip().strip('"').strip("'")
    return values


def write_vars(updates: dict[str, str], path: Path = GROUP_VARS) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    seen: set[str] = set()
    next_lines: list[str] = []
    for line in lines:
        match = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", line)
        if match and match.group(1) in updates:
            variable = match.group(1)
            next_lines.append(f"{variable}: {updates[variable]}")
            seen.add(variable)
        else:
            next_lines.append(line)

    missing = set(updates) - seen
    if missing:
        names = ", ".join(sorted(missing))
        raise VersionSyncError(f"Cannot update missing variable(s) in {path}: {names}")

    path.write_text("\n".join(next_lines) + "\n", encoding="utf-8")


def strip_prefix(value: str, prefix: str) -> str:
    if prefix and value.startswith(prefix):
        return value[len(prefix) :]
    return value


def asset_names(release: dict[str, Any]) -> set[str]:
    return {asset.get("name", "") for asset in release.get("assets", [])}


def validate_assets(source: Source, release: dict[str, Any], version: str) -> str:
    if not source.assets:
        return ""
    expected = {asset.format(version=version) for asset in source.assets}
    missing = sorted(expected - asset_names(release))
    if missing:
        raise BlockedUpdateError(
            f"{source.name} {version} is missing required asset(s): {', '.join(missing)}"
        )
    return "assets verified"


def github_release(source: Source) -> tuple[str, str]:
    if source.repo is None:
        raise VersionSyncError(f"{source.name} is missing a GitHub repo")

    base = f"https://api.github.com/repos/{source.repo}"
    try:
        release = fetch_json(f"{base}/releases/latest")
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        releases = fetch_json(f"{base}/releases?per_page=10")
        release = next(
            (
                item
                for item in releases
                if not item.get("draft") and not item.get("prerelease")
            ),
            None,
        )
        if release is None:
            tags = fetch_json(f"{base}/tags?per_page=1")
            if not tags:
                raise VersionSyncError(f"{source.name} has no releases or tags")
            release = {"tag_name": tags[0]["name"], "assets": []}

    tag = release.get("tag_name")
    if not tag:
        raise VersionSyncError(f"{source.name} release has no tag_name")

    version = strip_prefix(tag, source.tag_prefix)
    note = validate_assets(source, release, version)
    return version, note


def go_latest(_: Source) -> tuple[str, str]:
    releases = fetch_json("https://go.dev/dl/?mode=json")
    for release in releases:
        version = release.get("version", "")
        if not version or "rc" in version or "beta" in version:
            continue
        files = {item.get("filename", "") for item in release.get("files", [])}
        linux = f"{version}.linux-amd64.tar.gz"
        darwin = f"{version}.darwin-arm64.tar.gz"
        missing = sorted({linux, darwin} - files)
        if missing:
            raise VersionSyncError(
                f"Go {version.removeprefix('go')} is missing required file(s): {', '.join(missing)}"
            )
        return version.removeprefix("go"), "linux amd64 and darwin arm64 files verified"
    raise VersionSyncError("No stable Go release found")


def node_lts_major(_: Source) -> tuple[str, str]:
    releases = fetch_json("https://nodejs.org/dist/index.json")
    majors: set[int] = set()
    for release in releases:
        version = release.get("version", "")
        if not release.get("lts") or not version.startswith("v"):
            continue
        major = int(version.split(".", 1)[0].removeprefix("v"))
        if major % 2 == 0:
            majors.add(major)
    if not majors:
        raise VersionSyncError("No Node.js LTS release found")
    return str(max(majors)), "latest LTS major"


def resolve(source: Source) -> tuple[str | None, str]:
    providers: dict[str, Callable[[Source], tuple[str, str]]] = {
        "github": github_release,
        "go": go_latest,
        "node_lts_major": node_lts_major,
    }
    if source.provider == "manual":
        return None, source.note
    if source.provider not in providers:
        raise VersionSyncError(f"Unsupported provider {source.provider}")
    return providers[source.provider](source)


def collect_results(values: dict[str, str]) -> list[Result]:
    results: list[Result] = []
    for source in SOURCES:
        current = values.get(source.variable)
        if current is None:
            results.append(Result(source, "-", None, "error", "missing variable"))
            continue
        try:
            latest, note = resolve(source)
        except BlockedUpdateError as exc:
            results.append(Result(source, current, None, "blocked", str(exc)))
            continue
        except Exception as exc:  # noqa: BLE001 - report all per-tool failures.
            results.append(Result(source, current, None, "error", str(exc)))
            continue

        if latest is None:
            results.append(Result(source, current, None, "manual", note))
        elif latest != current:
            results.append(Result(source, current, latest, "update", note))
        else:
            results.append(Result(source, current, latest, "current", note))
    return results


def print_results(results: list[Result]) -> None:
    columns = ("Tool", "Variable", "Current", "Latest", "Status")
    rows = [
        (
            result.source.name,
            result.source.variable,
            result.current,
            result.latest or "-",
            result.status,
        )
        for result in results
    ]
    widths = [
        max(len(str(row[index])) for row in (columns, *rows))
        for index in range(len(columns))
    ]
    print("  ".join(column.ljust(widths[index]) for index, column in enumerate(columns)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)))

    notes = [result for result in results if result.note]
    if notes:
        print()
        for result in notes:
            print(f"{result.source.name}: {result.note}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report or update pinned tool versions in group_vars/all."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 when automatic updates are available.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Rewrite group_vars/all with the latest automatic versions.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    values = load_vars()
    results = collect_results(values)
    print_results(results)

    errors = [result for result in results if result.status == "error"]
    updates = {
        result.source.variable: result.latest
        for result in results
        if result.is_update and result.latest is not None
    }

    if args.write and updates:
        write_vars(updates)
        print()
        print(f"Updated {len(updates)} variable(s) in {GROUP_VARS.relative_to(REPO_ROOT)}.")

    if errors:
        return 2
    if args.check and updates:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
