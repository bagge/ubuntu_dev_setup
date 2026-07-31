#!/usr/bin/env bash
set -euo pipefail

ubuntu_version="${1:-26.04}"
runtime="${CONTAINER_RUNTIME:-docker}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
image="ubuntu-dev-setup-test:${ubuntu_version}"

case "${ubuntu_version}" in
    22.04 | 24.04 | 26.04) ;;
    *)
        echo "error: unsupported Ubuntu test version ${ubuntu_version}; expected 22.04, 24.04, or 26.04" >&2
        exit 1
        ;;
esac

"${runtime}" build \
    --build-arg "UBUNTU_VERSION=${ubuntu_version}" \
    --tag "${image}" \
    --file "${repo_root}/tests/container/Dockerfile" \
    "${repo_root}"

"${runtime}" run --rm \
    --mount "type=bind,src=${repo_root},dst=/src,readonly" \
    "${image}"
