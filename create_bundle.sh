#!/usr/bin/env bash
set -euo pipefail

FILE_LIST=(
    ".bash_history"
    ".bash_credentials"
    ".flexlmrc"
    ".gitconfig"
    ".git-credentials"
    ".netrc"
    ".qnx"
    ".ssh"
    ".config/google-chrome/Default/Bookmarks"
    ".config/opencode/opencode.json"
)

OUTPUT_FILE="sensitive-transfer-bundle.tar.gz"

umask 077

existing_paths=()
for path in "${FILE_LIST[@]}"; do
    if [[ -e "${HOME}/${path}" ]]; then
        existing_paths+=("${path}")
    else
        echo "warning: skipping missing path: ${path}" >&2
    fi
done

if [[ "${#existing_paths[@]}" -eq 0 ]]; then
    echo "error: none of the configured transfer paths exist in ${HOME}" >&2
    exit 1
fi

rm -f "${OUTPUT_FILE}"
tar -C "${HOME}" -czvf "${OUTPUT_FILE}" "${existing_paths[@]}"
