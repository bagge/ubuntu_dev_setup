#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
second_run_log="${TMPDIR:-/tmp}/ansible-macos-second-run.log"

if [ "$(uname -s)" != "Darwin" ]; then
  echo "macOS integration tests must run on macOS" >&2
  exit 1
fi

if [ "$(uname -m)" != "arm64" ]; then
  echo "macOS integration tests require Apple Silicon" >&2
  exit 1
fi

export ANSIBLE_CONFIG="${repo_root}/ansible.cfg"
export ANSIBLE_BECOME_ASK_PASS=False
export ANSIBLE_FORCE_COLOR=0
export TEST_EXTRA_VARS="test_mode=true homebrew_update=false install_google_chrome=false install_omnissa_horizon=false install_nvim_tools=false macos_set_login_shell=false run_desktop_customization=false"

cd "${repo_root}"

ansible-galaxy collection install -r requirements.yml
ansible-playbook setup.yml --syntax-check --extra-vars "${TEST_EXTRA_VARS}"
ansible-playbook setup.yml --extra-vars "${TEST_EXTRA_VARS}"
ansible-playbook tests/verify/macos.yml --extra-vars "${TEST_EXTRA_VARS}"
ansible-playbook setup.yml --extra-vars "${TEST_EXTRA_VARS}" | tee "${second_run_log}"
python3 tests/assert_ansible_recap.py "${second_run_log}" --changed 0 --failed 0
bash tests/shell/check.sh
