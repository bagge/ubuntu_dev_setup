#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

ubuntu_version="26.04"
name=""
cpus="4"
memory="6G"
disk="60G"
recreate=false
delete=false
sync_only=false

usage() {
    cat <<'USAGE'
Usage: bash tests/vm/run.sh [options] [22.04|24.04|26.04]

Create a Multipass Ubuntu GNOME VM for manual desktop testing.

Options:
  --recreate      Delete and recreate the VM before provisioning.
  --delete        Delete the VM and purge it from Multipass.
  --sync          Re-sync the repo to an existing VM without recreating it.
  --name NAME     Override the Multipass instance name.
  --cpus N        CPU count for new VMs. Default: 4.
  --memory SIZE   Memory for new VMs. Default: 6G.
  --disk SIZE     Disk size for new VMs. Default: 60G.
  -h, --help      Show this help.
USAGE
}

fail() {
    echo "error: $*" >&2
    exit 1
}

validate_name() {
    if [[ ! "$1" =~ ^[a-z][a-z0-9-]*[a-z0-9]$ ]]; then
        fail "invalid VM name '$1'; use lowercase letters, numbers, and dashes, starting with a letter"
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --recreate)
            recreate=true
            shift
            ;;
        --delete)
            delete=true
            shift
            ;;
        --sync)
            sync_only=true
            shift
            ;;
        --name)
            [[ $# -ge 2 ]] || fail "--name requires a value"
            name="$2"
            shift 2
            ;;
        --cpus)
            [[ $# -ge 2 ]] || fail "--cpus requires a value"
            cpus="$2"
            shift 2
            ;;
        --memory)
            [[ $# -ge 2 ]] || fail "--memory requires a value"
            memory="$2"
            shift 2
            ;;
        --disk)
            [[ $# -ge 2 ]] || fail "--disk requires a value"
            disk="$2"
            shift 2
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        22.04 | 24.04 | 26.04)
            ubuntu_version="$1"
            shift
            ;;
        *)
            fail "unknown argument: $1"
            ;;
    esac
done

if [[ -z "${name}" ]]; then
    name="ubuntu-dev-setup-gnome-${ubuntu_version//./-}"
fi
validate_name "${name}"

command -v multipass >/dev/null 2>&1 || fail "multipass is required"
command -v python3 >/dev/null 2>&1 || fail "python3 is required"
command -v tar >/dev/null 2>&1 || fail "tar is required"

# Multipass uses a bridge on a private subnet (typically 10.x). A VPN
# tunnel interface can shadow that subnet, making the VM unreachable.
if ip -o link show up 2>/dev/null | grep -v 'tap-' | grep -q 'POINTOPOINT'; then
    echo "warning: a VPN tunnel interface was detected. This may prevent" >&2
    echo "         multipass from reaching the VM. If the launch fails or" >&2
    echo "         the VM is unreachable, disconnect the VPN and retry." >&2
fi

cache_dir="${HOME}/.cache/ubuntu-dev-setup/gnome-vm/${name}"
password_file="${cache_dir}/password"
runtime_dir="${repo_root}/tests/vm/runtime/${name}"

instance_exists() {
    multipass list --format csv 2>/dev/null | grep -q "^${name},"
}

delete_instance() {
    if instance_exists; then
        multipass delete --purge "${name}"
        rm -rf "${cache_dir}"
        rm -rf "${runtime_dir}"
    else
        echo "VM ${name} does not exist."
    fi
}

ensure_password() {
    mkdir -p "${cache_dir}"
    chmod 0700 "${cache_dir}"
    if [[ ! -f "${password_file}" ]]; then
        python3 -c 'import random, string; print("ubuntu" + "".join(random.SystemRandom().choice(string.digits) for _ in range(3)))' >"${password_file}"
        chmod 0600 "${password_file}"
    fi
}

create_cloud_init() {
    local password="$1"
    local cloud_init="$2"

    if [[ "${ubuntu_version}" == "26.04" ]]; then
        cat >"${cloud_init}" <<EOF
#cloud-config
package_update: true
package_upgrade: false
packages:
  - dbus-x11
  - dconf-cli
  - git
  - gnome-remote-desktop
  - gnome-shell-extensions
  - openssl
  - python3-pip
  - shellcheck
write_files:
  - path: /etc/NetworkManager/conf.d/90-cloud-init-unmanaged.conf
    content: |
      [main]
      plugins=keyfile
      [keyfile]
      unmanaged-devices=type:ethernet
  - path: /etc/netplan/99-keep-networkd.yaml
    content: |
      network:
        version: 2
        renderer: networkd
chpasswd:
  expire: false
  users:
    - name: ubuntu
      password: "${password}"
      type: text
runcmd:
  - DEBIAN_FRONTEND=noninteractive apt-get install -y systemd
  - PIP_BREAK_SYSTEM_PACKAGES=1 pip3 install ansible
EOF
        return
    fi

    cat >"${cloud_init}" <<EOF
#cloud-config
package_update: true
package_upgrade: false
packages:
  - dbus-x11
  - dconf-cli
  - git
  - gnome-shell-extensions
  - python3-pip
  - shellcheck
  - xrdp
write_files:
  - path: /etc/NetworkManager/conf.d/90-cloud-init-unmanaged.conf
    content: |
      [main]
      plugins=keyfile
      [keyfile]
      unmanaged-devices=type:ethernet
  - path: /etc/netplan/99-keep-networkd.yaml
    content: |
      network:
        version: 2
        renderer: networkd
chpasswd:
  expire: false
  users:
    - name: ubuntu
      password: "${password}"
      type: text
runcmd:
  - DEBIAN_FRONTEND=noninteractive apt-get install -y systemd
  - PIP_BREAK_SYSTEM_PACKAGES=1 pip3 install ansible
  - systemctl enable --now xrdp
  - adduser xrdp ssl-cert
EOF
}

launch_instance() {
    local output

    if output="$(multipass launch "${ubuntu_version}" \
        --name "${name}" \
        --cpus "${cpus}" \
        --memory "${memory}" \
        --disk "${disk}" \
        --cloud-init "${cloud_init}" 2>&1)"; then
        return 0
    fi

    printf '%s\n' "${output}" >&2
    if [[ "${output}" == *"timed out"* ]] && instance_exists; then
        echo "Multipass launch timed out, but ${name} exists. Recovering..." >&2
        multipass stop "${name}" 2>/dev/null || true
        sleep 5
        multipass start "${name}" 2>/dev/null || true
        return 0
    fi

    return 1
}

wait_for_ssh() {
    local max_attempts=60
    local attempt=0
    while ! multipass exec "${name}" -- true >/dev/null 2>&1; do
        attempt=$((attempt + 1))
        if [[ "${attempt}" -ge "${max_attempts}" ]]; then
            fail "VM ${name} did not become SSH-accessible after ${max_attempts} attempts"
        fi
        echo "Waiting for VM connectivity... (${attempt}/${max_attempts})" >&2
        sleep 10
    done
}

install_desktop() {
    echo "Installing ubuntu-desktop (this may take several minutes)..." >&2
    multipass exec "${name}" -- sudo bash -c \
        'DEBIAN_FRONTEND=noninteractive apt-get install -y ubuntu-desktop'
    echo "Rebooting VM after desktop installation..." >&2
    if ! multipass restart "${name}" 2>/dev/null; then
        echo "Warning: 'multipass restart' failed — attempting stop/start cycle..." >&2
        multipass stop "${name}" 2>/dev/null || true
        sleep 2
        multipass start "${name}" 2>/dev/null || true
    fi
    wait_for_ssh
}

configure_gnome_remote_desktop() {
    [[ "${ubuntu_version}" == "26.04" ]] || return 0

    echo "Configuring GNOME Remote Desktop..." >&2
    multipass exec "${name}" -- sudo bash -s -- "${password}" <<'GUEST'
set -euo pipefail

rdp_password="$1"
tls_dir=/etc/gnome-remote-desktop
tls_cert="${tls_dir}/rdp-tls.crt"
tls_key="${tls_dir}/rdp-tls.key"

install -d -o gnome-remote-desktop -g gnome-remote-desktop -m 0755 "${tls_dir}"
if [[ ! -s "${tls_cert}" || ! -s "${tls_key}" ]]; then
    openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
        -subj /CN=ubuntu-dev-setup-gnome \
        -keyout "${tls_key}" \
        -out "${tls_cert}"
fi
chown gnome-remote-desktop:gnome-remote-desktop "${tls_cert}" "${tls_key}"
chmod 0644 "${tls_cert}"
chmod 0600 "${tls_key}"

grdctl --system --headless rdp set-tls-cert "${tls_cert}"
grdctl --system --headless rdp set-tls-key "${tls_key}"
grdctl --system --headless rdp set-credentials ubuntu "${rdp_password}"
grdctl --system --headless rdp set-port 3389
grdctl --system --headless rdp disable-port-negotiation
grdctl --system --headless rdp disable-view-only
grdctl --system --headless rdp enable
systemctl enable --now gnome-remote-desktop.service
GUEST
}

wait_for_rdp() {
    local max_attempts=30
    local attempt=0

    while ! multipass exec "${name}" -- bash -c \
        'ss -H -ltn | grep -q ":3389 "' >/dev/null 2>&1; do
        attempt=$((attempt + 1))
        if [[ "${attempt}" -ge "${max_attempts}" ]]; then
            fail "RDP service did not listen on port 3389 after ${max_attempts} attempts"
        fi
        echo "Waiting for RDP service... (${attempt}/${max_attempts})" >&2
        sleep 2
    done
}

sync_repo() {
    local archive
    mkdir -p "${runtime_dir}"
    archive="${runtime_dir}/repo.tar.gz"
    rm -f "${archive}"
    trap 'rm -f "${archive}"' RETURN

    tar -C "${repo_root}" \
        --exclude=.git \
        --exclude=repos \
        --exclude=tarballs \
        --exclude=tests/vm/runtime \
        -czf "${archive}" .

    multipass exec "${name}" -- rm -rf /home/ubuntu/ubuntu_dev_setup /tmp/ubuntu_dev_setup.tar.gz
    multipass exec "${name}" -- mkdir -p /home/ubuntu/ubuntu_dev_setup
    multipass transfer "${archive}" "${name}:/tmp/ubuntu_dev_setup.tar.gz"
    multipass exec "${name}" -- tar -C /home/ubuntu/ubuntu_dev_setup -xzf /tmp/ubuntu_dev_setup.tar.gz
    multipass exec "${name}" -- chown -R ubuntu:ubuntu /home/ubuntu/ubuntu_dev_setup
    multipass exec "${name}" -- rm -f /tmp/ubuntu_dev_setup.tar.gz
}

prepare_repo() {
    multipass exec "${name}" -- sudo -H -u ubuntu bash -lc '
        set -euo pipefail
        cd /home/ubuntu/ubuntu_dev_setup
        ansible-galaxy collection install -r requirements.yml
    '
}

if "${delete}"; then
    delete_instance
    exit 0
fi

if "${sync_only}"; then
    instance_exists || fail "VM ${name} does not exist. Run without --sync to create it."
    multipass start "${name}" 2>/dev/null || true
    wait_for_ssh
    sync_repo
    prepare_repo
    ip_address="$(multipass info "${name}" | awk '/IPv4/ { print $2; exit }')"
    echo "Repo synced to ${name} (${ip_address:-unknown})."
    exit 0
fi

ensure_password
password="$(<"${password_file}")"

if "${recreate}" && instance_exists; then
    multipass delete --purge "${name}"
fi

if ! instance_exists; then
    mkdir -p "${runtime_dir}"
    chmod 0700 "${runtime_dir}"
    cloud_init="${runtime_dir}/cloud-init.yml"
    trap 'rm -f "${cloud_init}"' EXIT
    create_cloud_init "${password}" "${cloud_init}"
    chmod 0600 "${cloud_init}"
    launch_instance
else
    multipass start "${name}" >/dev/null
fi

wait_for_ssh
multipass exec "${name}" -- cloud-init status --wait

install_desktop

guest_arch="$(multipass exec "${name}" -- uname -m)"
if [[ "${guest_arch}" != "x86_64" ]]; then
    fail "unsupported guest architecture ${guest_arch}; this setup supports Ubuntu amd64"
fi

sync_repo
prepare_repo
configure_gnome_remote_desktop
wait_for_rdp

ip_address="$(multipass info "${name}" | awk '/IPv4/ { print $2; exit }')"
if [[ -z "${ip_address}" ]]; then
    fail "could not determine VM IPv4 address"
fi

if [[ "${ubuntu_version}" == "26.04" ]]; then
    rdp_backend="GNOME Remote Desktop (Wayland)"
else
    rdp_backend="xrdp"
fi

cat <<EOF
VM is ready.

Name: ${name}
Ubuntu: ${ubuntu_version}
Address: ${ip_address}
RDP: ${ip_address}:3389
RDP backend: ${rdp_backend}
Username: ubuntu
Password: ${password}

Open a shell:
  multipass shell ${name}

Run desktop setup from a GNOME Terminal inside the RDP session:
  cd /home/ubuntu/ubuntu_dev_setup
  ansible-playbook setup.yml --tags gnome-customization,kitty

Use tests/manual/gnome-vm.md for the manual pass/fail checks.
Delete the VM when finished:
  bash tests/vm/run.sh --delete ${ubuntu_version}
EOF
