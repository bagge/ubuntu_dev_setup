#!/usr/bin/env bash

setup_snippet_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
DEVENV_SETUP_PATH="$(cd "${setup_snippet_dir}/../.." && pwd -P)"
export DEVENV_SETUP_PATH
