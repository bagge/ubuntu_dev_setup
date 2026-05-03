#!/usr/bin/env bash

export PATH="${PATH}:${DEVENV_SETUP_PATH}/repos/fzf/bin"

eval "$(fzf --bash)"

# shellcheck source=/dev/null
source "${DEVENV_SETUP_PATH}/repos/fzf-git.sh/fzf-git.sh"
# Enable XON/XOFF flow-control to disable CTRL-S freezing the terminal which
# interferes with fzf-git.sh
stty -ixon
