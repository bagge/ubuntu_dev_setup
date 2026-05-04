#!/usr/bin/env bash
# shellcheck disable=SC2016
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y --no-install-recommends \
    ansible \
    bash \
    bzip2 \
    dconf-cli \
    file \
    fontconfig \
    git \
    gzip \
    man-db \
    shellcheck \
    unzip \
    xz-utils \
    zstd
rm -rf /var/lib/apt/lists/*

rm -rf /workspace
mkdir -p /workspace
tar -C /src \
    --exclude=.git \
    --exclude=tarballs \
    --exclude=repos \
    -cf - . | tar -C /workspace -xf -
chown -R devtester:devtester /workspace

export ANSIBLE_CONFIG=/workspace/tests/ansible.cfg
export ANSIBLE_FORCE_COLOR=0
export TEST_EXTRA_VARS="test_mode=true run_gnome_customization=false install_docker=false install_google_chrome=false install_omnissa_horizon=false install_nvim_tools=false replace_existing_dotfiles=true"

cd /workspace

sudo -H -u devtester env \
    ANSIBLE_CONFIG=/workspace/tests/ansible.cfg \
    ANSIBLE_FORCE_COLOR=0 \
    TEST_EXTRA_VARS="${TEST_EXTRA_VARS}" \
    bash -lc '
    set -euo pipefail
    cd /workspace
    ansible-galaxy collection install -r requirements.yml
    ansible-playbook setup.yml --syntax-check --extra-vars "${TEST_EXTRA_VARS}"
    ansible-playbook setup.yml --extra-vars "${TEST_EXTRA_VARS}"
    ansible-playbook setup.yml --tags gnome-customization,kitty --extra-vars "${TEST_EXTRA_VARS} run_desktop_customization=true" | tee /tmp/headless-desktop.log
    grep -F "Skipping Ubuntu GNOME customization because no usable graphical GNOME session was detected." /tmp/headless-desktop.log
    ansible-playbook tests/verify/guarded-links.yml
    ansible-playbook tests/verify/container.yml --extra-vars "${TEST_EXTRA_VARS}"
    ansible-playbook setup.yml --extra-vars "${TEST_EXTRA_VARS}" | tee /tmp/ansible-second-run.log
    python3 tests/assert_ansible_recap.py /tmp/ansible-second-run.log --changed 0 --failed 0
    bash tests/shell/check.sh
'
