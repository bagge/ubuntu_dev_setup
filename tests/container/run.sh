#!/usr/bin/env bash
set -euo pipefail

ubuntu_version="${1:-24.04}"
runtime="${CONTAINER_RUNTIME:-docker}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
image="ubuntu-dev-setup-test:${ubuntu_version}"

"${runtime}" build \
    --build-arg "UBUNTU_VERSION=${ubuntu_version}" \
    --tag "${image}" \
    --file "${repo_root}/tests/container/Dockerfile" \
    "${repo_root}"

"${runtime}" run --rm \
    --mount "type=bind,src=${repo_root},dst=/src,readonly" \
    "${image}"
