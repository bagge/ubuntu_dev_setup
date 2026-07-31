# Ubuntu 26.04 Release Check

Run this checklist before declaring Ubuntu 26.04 supported. Routine container
CI deliberately disables the heavyweight optional packages covered here.

## Automated Baseline

From the repository root, run:

```bash
bash tests/container/run.sh 26.04
```

The first playbook run and verification playbooks must succeed. The final
playbook run must report `changed=0` and `failed=0`.

## Desktop And Optional Packages

1. Create the disposable GNOME VM and connect to the printed RDP address:

   ```bash
   bash tests/vm/run.sh --recreate 26.04
   ```

2. From GNOME Terminal in the Wayland session, run the complete setup:

   ```bash
   cd /home/ubuntu/ubuntu_dev_setup
   ansible-playbook setup.yml --extra-vars replace_existing_dotfiles=true
   ```

3. Run the same command again. Require `failed=0`; investigate every repeated
   change before accepting idempotence.

4. Verify the managed Chrome repository and installation:

   ```bash
   test ! -e /etc/apt/sources.list.d/google-chrome.list
   test -s /etc/apt/keyrings/google-chrome.asc
   grep -Fx 'Signed-By: /etc/apt/keyrings/google-chrome.asc' \
     /etc/apt/sources.list.d/google-chrome.sources
   grep -Fx 'repo_add_once="false"' /etc/default/google-chrome
   grep -Fx 'repo_reenable_on_distupgrade="false"' /etc/default/google-chrome
   sudo apt-get update
   google-chrome --version
   ```

5. Verify Docker and its service:

   ```bash
   docker --version
   sudo systemctl is-active docker
   ```

   Log out and reconnect before requiring non-root Docker access because group
   membership changes do not affect an existing login session.

6. Verify Horizon and launch its graphical client:

   ```bash
   dpkg-query -W vmware-horizon-client
   vmware-view
   ```

   The client must open without a missing-library or display-backend error.

7. Verify the complete Neovim tooling path:

   ```bash
   nvim --version | head -n 1
   tree-sitter --version
   rustc --version
   node --version
   npm --version
   ```

8. Complete the GNOME checks in `tests/manual/gnome-vm.md`, including Wayland
   detection, keybindings, extensions, appearance, and kitty defaults.

## Pass Criteria

- The 26.04 container integration and its idempotence pass succeed.
- The full desktop playbook succeeds twice in a GNOME Wayland session.
