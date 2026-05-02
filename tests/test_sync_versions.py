import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import sync_versions


class SyncVersionsTest(unittest.TestCase):
    def test_load_vars_reads_simple_group_vars_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "all"
            path.write_text(
                "---\n"
                "nvim_version: 0.11.5\n"
                "node_major_version: 20\n"
                "horizon_deb: VMware-Horizon-Client-2406.x64.deb\n",
                encoding="utf-8",
            )

            self.assertEqual(
                sync_versions.load_vars(path),
                {
                    "nvim_version": "0.11.5",
                    "node_major_version": "20",
                    "horizon_deb": "VMware-Horizon-Client-2406.x64.deb",
                },
            )

    def test_write_vars_updates_only_requested_variables(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "all"
            path.write_text(
                "---\n"
                "nvim_version: 0.11.5\n"
                "homebrew_update: false\n"
                "node_major_version: 20\n",
                encoding="utf-8",
            )

            sync_versions.write_vars(
                {"nvim_version": "0.12.0", "node_major_version": "22"},
                path,
            )

            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "---\n"
                "nvim_version: 0.12.0\n"
                "homebrew_update: false\n"
                "node_major_version: 22\n",
            )

    def test_github_release_strips_prefix_and_verifies_assets(self):
        release = {
            "tag_name": "v1.2.3",
            "assets": [
                {"name": "tool-1.2.3-linux-amd64.tar.gz"},
                {"name": "tool-1.2.3-darwin-arm64.tar.gz"},
            ],
        }
        source = sync_versions.Source(
            "tool",
            "tool_version",
            "github",
            "owner/repo",
            "v",
            (
                "tool-{version}-linux-amd64.tar.gz",
                "tool-{version}-darwin-arm64.tar.gz",
            ),
        )

        with mock.patch.object(sync_versions, "fetch_json", return_value=release):
            self.assertEqual(
                sync_versions.github_release(source),
                ("1.2.3", "assets verified"),
            )

    def test_github_release_reports_missing_assets(self):
        release = {"tag_name": "v1.2.3", "assets": []}
        source = sync_versions.Source(
            "tool",
            "tool_version",
            "github",
            "owner/repo",
            "v",
            ("tool-{version}-linux-amd64.tar.gz",),
        )

        with mock.patch.object(sync_versions, "fetch_json", return_value=release):
            with self.assertRaisesRegex(
                sync_versions.VersionSyncError,
                "missing required asset",
            ):
                sync_versions.github_release(source)

    def test_go_latest_uses_first_stable_release_with_required_files(self):
        response = [
            {
                "version": "go1.25.5",
                "files": [
                    {"filename": "go1.25.5.linux-amd64.tar.gz"},
                    {"filename": "go1.25.5.darwin-arm64.tar.gz"},
                ],
            }
        ]

        with mock.patch.object(sync_versions, "fetch_json", return_value=response):
            self.assertEqual(
                sync_versions.go_latest(sync_versions.Source("Go", "golang_version", "go")),
                ("1.25.5", "linux amd64 and darwin arm64 files verified"),
            )

    def test_node_lts_major_uses_highest_lts_major(self):
        response = [
            {"version": "v25.0.0", "lts": False},
            {"version": "v24.1.0", "lts": "Krypton"},
            {"version": "v22.10.0", "lts": "Jod"},
            {"version": "v20.19.0", "lts": "Iron"},
        ]

        with mock.patch.object(sync_versions, "fetch_json", return_value=response):
            self.assertEqual(
                sync_versions.node_lts_major(
                    sync_versions.Source(
                        "Node.js LTS major",
                        "node_major_version",
                        "node_lts_major",
                    )
                ),
                ("24", "latest LTS major"),
            )

    def test_collect_results_marks_manual_sources(self):
        values = {"horizon_deb": "VMware-Horizon-Client-2406.x64.deb"}
        source = sync_versions.Source(
            "Horizon",
            "horizon_deb",
            "manual",
            note="manual check required",
        )

        with mock.patch.object(sync_versions, "SOURCES", (source,)):
            self.assertEqual(
                sync_versions.collect_results(values),
                [
                    sync_versions.Result(
                        source,
                        "VMware-Horizon-Client-2406.x64.deb",
                        None,
                        "manual",
                        "manual check required",
                    )
                ],
            )


if __name__ == "__main__":
    unittest.main()
