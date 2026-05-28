#!/usr/bin/env python3
"""Report and update pinned tool versions and checksums used by the playbooks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
GROUP_VARS = REPO_ROOT / "group_vars" / "all"
TIMEOUT_SECONDS = 20
GIT_SHA256SUMS_URL = "https://mirrors.edge.kernel.org/pub/software/scm/git/sha256sums.asc"

ARTIFACTS = {
    "ubuntu_amd64": {
        "bazel_buildtools_target": "linux-amd64",
        "bazelisk_asset": "bazelisk-linux-amd64",
        "deb_arch": "amd64",
        "glow_deb_arch": "amd64",
        "golang_target": "linux-amd64",
        "github_cli_archive_ext": "tar.gz",
        "github_cli_target": "linux_amd64",
        "kitty_target": "x86_64",
        "mdcat_target": "x86_64-unknown-linux-gnu",
        "nvim_archive_name": "nvim-linux-x86_64",
        "toprepo_target": "linux-x86_64",
    },
    "macos_arm64": {
        "bazel_buildtools_target": "darwin-arm64",
        "bazelisk_asset": "bazelisk-darwin-arm64",
        "golang_target": "darwin-arm64",
        "github_cli_archive_ext": "zip",
        "github_cli_target": "macOS_arm64",
        "mdcat_target": "aarch64-apple-darwin",
        "nvim_archive_name": "nvim-macos-arm64",
    },
}
UBUNTU = ARTIFACTS["ubuntu_amd64"]
MACOS = ARTIFACTS["macos_arm64"]


@dataclass(frozen=True)
class ChecksumAsset:
    name: str
    variable: str
    url: str | None = None


@dataclass(frozen=True)
class Source:
    name: str
    variable: str
    provider: str
    repo: str | None = None
    tag_prefix: str = ""
    assets: tuple[str, ...] = ()
    note: str = ""
    checksum_assets: tuple[ChecksumAsset, ...] = ()


SOURCES: tuple[Source, ...] = (
    Source("Bash-it", "bash_it_version", "github", "Bash-it/bash-it", "v"),
    Source(
        "gitstatus",
        "gitstatus_commit",
        "github_default_branch",
        "romkatv/gitstatus",
    ),
    Source(
        "Bazel buildtools",
        "bazel_buildtools_version",
        "github",
        "bazelbuild/buildtools",
        "v",
        (
            f"buildifier-{UBUNTU['bazel_buildtools_target']}",
            f"buildifier-{MACOS['bazel_buildtools_target']}",
            f"buildozer-{UBUNTU['bazel_buildtools_target']}",
            f"buildozer-{MACOS['bazel_buildtools_target']}",
        ),
        checksum_assets=(
            ChecksumAsset(
                f"buildifier-{UBUNTU['bazel_buildtools_target']}",
                "bazel_buildifier_linux_checksum",
            ),
            ChecksumAsset(
                f"buildifier-{MACOS['bazel_buildtools_target']}",
                "bazel_buildifier_macos_checksum",
            ),
            ChecksumAsset(
                f"buildozer-{UBUNTU['bazel_buildtools_target']}",
                "bazel_buildozer_linux_checksum",
            ),
            ChecksumAsset(
                f"buildozer-{MACOS['bazel_buildtools_target']}",
                "bazel_buildozer_macos_checksum",
            ),
        ),
    ),
    Source(
        "Bazelisk",
        "bazelisk_version",
        "github",
        "bazelbuild/bazelisk",
        "v",
        (UBUNTU["bazelisk_asset"], MACOS["bazelisk_asset"]),
        checksum_assets=(
            ChecksumAsset(UBUNTU["bazelisk_asset"], "bazelisk_linux_checksum"),
            ChecksumAsset(MACOS["bazelisk_asset"], "bazelisk_macos_checksum"),
        ),
    ),
    Source("fzf", "fzf_version", "github", "junegunn/fzf", "v"),
    Source(
        "fzf-git.sh",
        "fzf_git_commit",
        "github_default_branch",
        "junegunn/fzf-git.sh",
    ),
    Source(
        "glow",
        "glow_version",
        "github",
        "charmbracelet/glow",
        "v",
        (f"glow_{{version}}_{UBUNTU['glow_deb_arch']}.deb",),
        checksum_assets=(
            ChecksumAsset(
                f"glow_{{version}}_{UBUNTU['glow_deb_arch']}.deb",
                "glow_ubuntu_checksum",
            ),
        ),
    ),
    Source(
        "Go",
        "golang_version",
        "go",
        checksum_assets=(
            ChecksumAsset(
                f"go{{version}}.{UBUNTU['golang_target']}.tar.gz",
                "golang_linux_checksum",
            ),
            ChecksumAsset(
                f"go{{version}}.{MACOS['golang_target']}.tar.gz",
                "golang_macos_checksum",
            ),
        ),
    ),
    Source("Git", "git_version", "kernel_git"),
    Source(
        "GitHub CLI",
        "github_cli_version",
        "github",
        "cli/cli",
        "v",
        (
            f"gh_{{version}}_{UBUNTU['github_cli_target']}.{UBUNTU['github_cli_archive_ext']}",
            f"gh_{{version}}_{MACOS['github_cli_target']}.{MACOS['github_cli_archive_ext']}",
        ),
        checksum_assets=(
            ChecksumAsset(
                f"gh_{{version}}_{UBUNTU['github_cli_target']}.{UBUNTU['github_cli_archive_ext']}",
                "github_cli_linux_checksum",
            ),
            ChecksumAsset(
                f"gh_{{version}}_{MACOS['github_cli_target']}.{MACOS['github_cli_archive_ext']}",
                "github_cli_macos_checksum",
            ),
        ),
    ),
    Source(
        "Homebrew installer",
        "homebrew_install_url",
        "static_url",
        note="Mutable upstream installer URL pinned by checksum.",
        checksum_assets=(
            ChecksumAsset("{homebrew_install_url}", "homebrew_install_checksum"),
        ),
    ),
    Source(
        "kitty",
        "kitty_version",
        "github",
        "kovidgoyal/kitty",
        "v",
        (f"kitty-{{version}}-{UBUNTU['kitty_target']}.txz",),
        checksum_assets=(
            ChecksumAsset(
                f"kitty-{{version}}-{UBUNTU['kitty_target']}.txz",
                "kitty_linux_checksum",
            ),
        ),
    ),
    Source(
        "kitty-themes",
        "kitty_themes_commit",
        "github_default_branch",
        "kovidgoyal/kitty-themes",
    ),
    Source(
        "kitty-grab",
        "kitty_grab_commit",
        "github_default_branch",
        "yurikhan/kitty_grab",
    ),
    Source(
        "mdcat",
        "mdcat_version",
        "github",
        "swsnr/mdcat",
        "mdcat-",
        (f"mdcat-{{version}}-{UBUNTU['mdcat_target']}.tar.gz",),
        "Ubuntu-only in this playbook.",
        checksum_assets=(
            ChecksumAsset(
                f"mdcat-{{version}}-{UBUNTU['mdcat_target']}.tar.gz",
                "mdcat_linux_checksum",
            ),
        ),
    ),
    Source(
        "Nerd Fonts",
        "nerd_fonts_version",
        "github",
        "ryanoasis/nerd-fonts",
        "v",
        ("Hack.zip",),
        checksum_assets=(
            ChecksumAsset("Hack.zip", "nerd_fonts_hack_checksum"),
        ),
    ),
    Source("Node.js LTS major", "node_major_version", "node_lts_major"),
    Source(
        "nvm",
        "nvm_version",
        "github",
        "nvm-sh/nvm",
        "v",
        checksum_assets=(
            ChecksumAsset(
                "install.sh",
                "nvm_install_checksum",
                "https://raw.githubusercontent.com/nvm-sh/nvm/v{version}/install.sh",
            ),
        ),
    ),
    Source(
        "Neovim",
        "nvim_version",
        "github",
        "neovim/neovim",
        "v",
        (
            f"{UBUNTU['nvim_archive_name']}.tar.gz",
            f"{MACOS['nvim_archive_name']}.tar.gz",
        ),
        checksum_assets=(
            ChecksumAsset(
                f"{UBUNTU['nvim_archive_name']}.tar.gz",
                "nvim_linux_checksum",
            ),
            ChecksumAsset(
                f"{MACOS['nvim_archive_name']}.tar.gz",
                "nvim_macos_checksum",
            ),
        ),
    ),
    Source(
        "PlantUML",
        "plantuml_version",
        "github",
        "plantuml/plantuml",
        "v",
        ("plantuml-{version}.jar",),
        checksum_assets=(
            ChecksumAsset("plantuml-{version}.jar", "plantuml_checksum"),
        ),
    ),
    Source(
        "repo tool",
        "repo_tool_url",
        "static_url",
        note="Mutable upstream script URL pinned by checksum.",
        checksum_assets=(
            ChecksumAsset("{repo_tool_url}", "repo_tool_checksum"),
        ),
    ),
    Source(
        "rustup",
        "rustup_version",
        "static_url",
        note="Rustup archive version is pinned manually; checksum is refreshed from static.rust-lang.org.",
        checksum_assets=(
            ChecksumAsset(
                "rustup-init",
                "rustup_init_linux_checksum",
                "https://static.rust-lang.org/rustup/archive/{version}/x86_64-unknown-linux-gnu/rustup-init",
            ),
        ),
    ),
    Source("Tree-sitter", "tree_sitter_version", "github", "tree-sitter/tree-sitter", "v"),
    Source("vale-ls", "vale_ls_version", "github", "vale-cli/vale-ls", "v"),
    Source(
        "toprepo",
        "toprepo_version",
        "github",
        "meroton/git-toprepo",
        "",
        (f"git-toprepo-{{version}}-{UBUNTU['toprepo_target']}",),
        checksum_assets=(
            ChecksumAsset(
                f"git-toprepo-{{version}}-{UBUNTU['toprepo_target']}",
                "toprepo_linux_checksum",
            ),
        ),
    ),
    Source(
        "Omnissa Horizon Client",
        "horizon_deb",
        "manual",
        note="Vendor download pages do not expose a stable version API; update horizon_url and horizon_deb manually.",
        checksum_assets=(
            ChecksumAsset("{horizon_url}/{horizon_deb}", "horizon_deb_checksum"),
        ),
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
    updates: dict[str, str] = field(default_factory=dict)

    @property
    def is_update(self) -> bool:
        return self.status == "update"

    @property
    def has_updates(self) -> bool:
        return bool(self.updates)


class VersionSyncError(RuntimeError):
    pass


class BlockedUpdateError(VersionSyncError):
    pass


def request_headers(accept: str = "application/vnd.github+json") -> dict[str, str]:
    headers = {
        "Accept": accept,
        "User-Agent": "ubuntu-dev-setup-version-sync",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token and "github" in accept:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _urlopen_with_retry(
    request: urllib.request.Request,
    *,
    max_retries: int = 4,
) -> Any:
    """Open *request*, retrying on 403/429 rate-limit responses with backoff."""
    for attempt in range(max_retries + 1):
        try:
            return urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            retryable = exc.code in (403, 429) and "rate limit" in body.lower()
            if not retryable or attempt == max_retries:
                raise
            wait = 2 ** attempt
            retry_after = exc.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                wait = max(wait, int(retry_after))
            print(
                f"  Rate-limited; retrying in {wait}s "
                f"(attempt {attempt + 1}/{max_retries})...",
                file=sys.stderr,
            )
            time.sleep(wait)
    raise RuntimeError("unreachable")


def fetch_json(url: str) -> Any:
    headers = request_headers()
    request = urllib.request.Request(url, headers=headers)
    with _urlopen_with_retry(request) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers=request_headers("text/plain"))
    with _urlopen_with_retry(request) as response:
        return response.read().decode("utf-8")


def fetch_sha256(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers=request_headers("application/octet-stream"),
    )
    digest = hashlib.sha256()
    with _urlopen_with_retry(request) as response:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


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

    for variable in sorted(set(updates) - seen):
        next_lines.append(f"{variable}: {updates[variable]}")

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


def format_asset(template: str, version: str, values: dict[str, str]) -> str:
    return template.format(version=version, **values)


def github_release_for_version(source: Source, version: str) -> dict[str, Any]:
    if source.repo is None:
        raise VersionSyncError(f"{source.name} is missing a GitHub repo")
    tag = urllib.parse.quote(f"{source.tag_prefix}{version}", safe="")
    return fetch_json(f"https://api.github.com/repos/{source.repo}/releases/tags/{tag}")


def github_asset_map(release: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        asset.get("name", ""): asset
        for asset in release.get("assets", [])
        if asset.get("name")
    }


def github_asset_checksums(
    source: Source,
    version: str,
    values: dict[str, str],
    release: dict[str, Any] | None = None,
) -> dict[str, str]:
    if not source.checksum_assets:
        return {}
    release = release or github_release_for_version(source, version)
    assets = github_asset_map(release)
    checksums: dict[str, str] = {}
    missing: list[str] = []
    for asset in source.checksum_assets:
        name = format_asset(asset.name, version, values)
        metadata = assets.get(name)
        if metadata is None and asset.url is None:
            missing.append(name)
            continue
        digest = metadata.get("digest") if metadata else None
        if isinstance(digest, str) and digest.startswith("sha256:"):
            checksums[asset.variable] = digest.removeprefix("sha256:")
            continue
        url = asset.url or metadata.get("browser_download_url")
        if not url:
            missing.append(f"{name} checksum")
            continue
        checksums[asset.variable] = fetch_sha256(format_asset(url, version, values))
    if missing:
        raise BlockedUpdateError(
            f"{source.name} {version} is missing required asset(s): {', '.join(missing)}"
        )
    return checksums


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


def github_default_branch_commit(source: Source) -> tuple[str, str]:
    if source.repo is None:
        raise VersionSyncError(f"{source.name} is missing a GitHub repo")

    base = f"https://api.github.com/repos/{source.repo}"
    metadata = fetch_json(base)
    default_branch = metadata.get("default_branch")
    if not default_branch:
        raise VersionSyncError(f"{source.name} repository has no default_branch")

    branch_ref = urllib.parse.quote(default_branch, safe="")
    commit = fetch_json(f"{base}/commits/{branch_ref}")
    sha = commit.get("sha")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise VersionSyncError(f"{source.name} default branch commit has no full SHA")
    return sha, f"default branch: {default_branch}"


def go_latest(_: Source) -> tuple[str, str]:
    releases = fetch_json("https://go.dev/dl/?mode=json")
    for release in releases:
        version = release.get("version", "")
        if not version or "rc" in version or "beta" in version:
            continue
        files = {item.get("filename", "") for item in release.get("files", [])}
        linux = f"{version}.{UBUNTU['golang_target']}.tar.gz"
        darwin = f"{version}.{MACOS['golang_target']}.tar.gz"
        missing = sorted({linux, darwin} - files)
        if missing:
            raise VersionSyncError(
                f"Go {version.removeprefix('go')} is missing required file(s): {', '.join(missing)}"
            )
        return version.removeprefix("go"), "linux amd64 and darwin arm64 files verified"
    raise VersionSyncError("No stable Go release found")


def go_release(version: str) -> dict[str, Any]:
    full_version = f"go{version}"
    for release in fetch_json("https://go.dev/dl/?mode=json"):
        if release.get("version") == full_version:
            return release
    raise VersionSyncError(f"Go {version} was not found in release metadata")


def version_key(version: str) -> tuple[int, int, int]:
    parts = version.split(".")
    if len(parts) != 3:
        raise VersionSyncError(f"Unsupported semantic version: {version}")
    return tuple(int(part) for part in parts)


def kernel_git_checksums_from_text(text: str) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^([0-9a-f]{64})\s+git-(\d+\.\d+\.\d+)\.tar\.xz$", line)
        if match:
            checksums[match.group(2)] = match.group(1)
    if not checksums:
        raise VersionSyncError("No stable Git source checksums found")
    return checksums


def kernel_git_latest(_: Source) -> tuple[str, str]:
    checksums = kernel_git_checksums_from_text(fetch_text(GIT_SHA256SUMS_URL))
    latest = max(checksums, key=version_key)
    return latest, "kernel.org source tarball"


def kernel_git_checksums(version: str) -> dict[str, str]:
    checksums = kernel_git_checksums_from_text(fetch_text(GIT_SHA256SUMS_URL))
    checksum = checksums.get(version)
    if checksum is None:
        raise BlockedUpdateError(f"Git {version} source checksum was not found")
    return {"git_source_checksum": checksum}


def go_checksums(
    source: Source,
    version: str,
    values: dict[str, str],
    release: dict[str, Any] | None = None,
) -> dict[str, str]:
    if not source.checksum_assets:
        return {}
    try:
        release = release or go_release(version)
    except VersionSyncError:
        return {
            asset.variable: fetch_sha256(
                f"https://go.dev/dl/{format_asset(asset.name, version, values)}"
            )
            for asset in source.checksum_assets
        }
    files = {item.get("filename", ""): item for item in release.get("files", [])}
    checksums: dict[str, str] = {}
    missing: list[str] = []
    for asset in source.checksum_assets:
        name = format_asset(asset.name, version, values)
        file_info = files.get(name)
        sha256 = file_info.get("sha256") if file_info else None
        if not sha256:
            missing.append(name)
        else:
            checksums[asset.variable] = sha256
    if missing:
        raise BlockedUpdateError(
            f"Go {version} is missing required file(s): {', '.join(missing)}"
        )
    return checksums


def direct_checksums(
    source: Source,
    version: str,
    values: dict[str, str],
) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for asset in source.checksum_assets:
        url = format_asset(asset.url or asset.name, version, values)
        checksums[asset.variable] = fetch_sha256(url)
    return checksums


def checksum_values(
    source: Source,
    version: str,
    values: dict[str, str],
) -> dict[str, str]:
    if source.provider == "github":
        return github_asset_checksums(source, version, values)
    if source.provider == "go":
        return go_checksums(source, version, values)
    if source.provider == "kernel_git":
        return kernel_git_checksums(version)
    if source.provider in {"manual", "static_url"}:
        return direct_checksums(source, version, values)
    return {}


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
        "github_default_branch": github_default_branch_commit,
        "go": go_latest,
        "kernel_git": kernel_git_latest,
        "node_lts_major": node_lts_major,
    }
    if source.provider == "manual":
        return None, source.note
    if source.provider == "static_url":
        return None, source.note
    if source.provider not in providers:
        raise VersionSyncError(f"Unsupported provider {source.provider}")
    return providers[source.provider](source)


def result_updates(
    source: Source,
    values: dict[str, str],
    version: str,
    include_version: bool,
) -> dict[str, str]:
    updates: dict[str, str] = {}
    if include_version:
        updates[source.variable] = version
    for variable, checksum in checksum_values(source, version, values).items():
        if values.get(variable) != checksum:
            updates[variable] = checksum
    return updates


def collect_results(
    values: dict[str, str],
    *,
    current_checksums: bool = False,
) -> list[Result]:
    results: list[Result] = []
    for source in SOURCES:
        current = values.get(source.variable)
        if current is None:
            results.append(Result(source, "-", None, "error", "missing variable"))
            continue
        if current_checksums:
            try:
                updates = result_updates(source, values, current, False)
            except Exception as exc:  # noqa: BLE001 - report all per-tool failures.
                results.append(Result(source, current, None, "error", str(exc)))
                continue
            status = "checksum" if updates else "current"
            if source.provider == "manual" and not updates:
                status = "manual"
            results.append(Result(source, current, current, status, source.note, updates))
            continue
        try:
            latest, note = resolve(source)
        except BlockedUpdateError as exc:
            try:
                updates = result_updates(source, values, current, False)
            except Exception:
                updates = {}
            results.append(Result(source, current, None, "blocked", str(exc), updates))
            continue
        except Exception as exc:  # noqa: BLE001 - report all per-tool failures.
            results.append(Result(source, current, None, "error", str(exc)))
            continue

        if latest is None:
            try:
                updates = result_updates(source, values, current, False)
            except Exception as exc:  # noqa: BLE001 - report checksum failures.
                results.append(Result(source, current, None, "error", str(exc)))
                continue
            if updates:
                status = "checksum"
            elif source.provider == "manual":
                status = "manual"
            else:
                status = "current"
            results.append(Result(source, current, None, status, note, updates))
            continue

        include_version = latest != current
        try:
            updates = result_updates(source, values, latest, include_version)
        except BlockedUpdateError as exc:
            results.append(Result(source, current, None, "blocked", str(exc)))
            continue
        status = "update" if include_version else "checksum" if updates else "current"
        results.append(Result(source, current, latest, status, note, updates))
    return results


def print_results(results: list[Result]) -> None:
    columns = ("Tool", "Variable", "Current", "Latest", "Status", "Vars")
    rows = [
        (
            result.source.name,
            result.source.variable,
            result.current,
            result.latest or "-",
            result.status,
            str(len(result.updates)) if result.updates else "-",
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
        help="Exit 1 when automatic version or checksum updates are available.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Rewrite group_vars/all with the latest automatic versions and checksums.",
    )
    parser.add_argument(
        "--write-current-checksums",
        action="store_true",
        help="Rewrite checksum variables for currently declared versions only.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not os.environ.get("GITHUB_TOKEN"):
        print(
            "hint: set GITHUB_TOKEN to avoid GitHub API rate limits (60 req/h unauthenticated).",
            file=sys.stderr,
        )
    values = load_vars()
    results = collect_results(values, current_checksums=args.write_current_checksums)
    print_results(results)

    errors = [result for result in results if result.status == "error"]
    updates: dict[str, str] = {}
    for result in results:
        updates.update(result.updates)

    if (args.write or args.write_current_checksums) and updates:
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
