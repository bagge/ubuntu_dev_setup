#!/usr/bin/env bash

BASH_CREDENTIALS="${HOME}/.bash_credentials"
if [ -f "${BASH_CREDENTIALS}" ]; then
    # shellcheck source=/dev/null
    source "${BASH_CREDENTIALS}"
fi
