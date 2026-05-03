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
)

tar -C "${HOME}" -czvf bundle.tar.gz "${FILE_LIST[@]}"
