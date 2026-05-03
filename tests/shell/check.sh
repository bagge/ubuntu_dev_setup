#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

bash_files=(
    bashrc
    bash_profile
    create_bundle.sh
    bashrc.d/000-setup-location.bashrc
    bashrc.d/001-homebrew.bashrc
    bashrc.d/002-bash_it.bashrc
    bashrc.d/003-bazel-helpers.bashrc
    bashrc.d/004-bash-history.bashrc
    bashrc.d/005-fzf.bashrc
    bashrc.d/006-nvm.bashrc
    bashrc.d/007-golang.bashrc
    bashrc.d/999-optional-auth.bashrc
    tests/container/run.sh
    tests/container/run-in-container.sh
    tests/macos/run.sh
    tests/shell/check.sh
)

for file in "${bash_files[@]}"; do
    bash -n "${file}"
done

python3 -m py_compile tools/sync_versions.py
python3 -m unittest tests/test_sync_versions.py

bundle_test_dir="$(mktemp -d)"
trap 'rm -rf "${bundle_test_dir}"' EXIT

bundle_home="${bundle_test_dir}/home"
bundle_output="${bundle_test_dir}/output"
mkdir -p "${bundle_home}/.ssh" "${bundle_output}"
printf '[user]\n\tname = Test User\n' >"${bundle_home}/.gitconfig"
printf 'Host example\n    HostName example.com\n' >"${bundle_home}/.ssh/config"

(
    cd "${bundle_output}"
    HOME="${bundle_home}" bash "${OLDPWD}/create_bundle.sh" >bundle.stdout 2>bundle.stderr
)

test -f "${bundle_output}/sensitive-transfer-bundle.tar.gz"
test ! -e "${bundle_output}/bundle.tar.gz"
bundle_mode="$(python3 -c 'import os, sys; print(format(os.stat(sys.argv[1]).st_mode & 0o777, "03o"))' "${bundle_output}/sensitive-transfer-bundle.tar.gz")"
test "${bundle_mode}" = "600"
tar -tzf "${bundle_output}/sensitive-transfer-bundle.tar.gz" | sort >"${bundle_output}/bundle.contents"
grep -Fx ".gitconfig" "${bundle_output}/bundle.contents" >/dev/null
grep -Fx ".ssh/" "${bundle_output}/bundle.contents" >/dev/null
grep -Fx ".ssh/config" "${bundle_output}/bundle.contents" >/dev/null
grep -F "warning: skipping missing path: .bash_history" "${bundle_output}/bundle.stderr" >/dev/null

empty_home="${bundle_test_dir}/empty-home"
empty_output="${bundle_test_dir}/empty-output"
mkdir -p "${empty_home}" "${empty_output}"
if (
    cd "${empty_output}"
    HOME="${empty_home}" bash "${OLDPWD}/create_bundle.sh" >bundle.stdout 2>bundle.stderr
); then
    echo "expected create_bundle.sh to fail when no configured paths exist" >&2
    exit 1
fi
test ! -e "${empty_output}/sensitive-transfer-bundle.tar.gz"
grep -F "error: none of the configured transfer paths exist" "${empty_output}/bundle.stderr" >/dev/null

if command -v shellcheck >/dev/null 2>&1; then
    shellcheck "${bash_files[@]}"
fi
