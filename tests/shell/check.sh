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

if command -v shellcheck >/dev/null 2>&1; then
    shellcheck \
        tests/container/run.sh \
        tests/container/run-in-container.sh \
        tests/macos/run.sh \
        tests/shell/check.sh
fi
