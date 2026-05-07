# Manual GNOME VM Test Runbook

Use this runbook for desktop behavior that cannot be validated reliably in a
container or a headless GitHub Actions runner.

## Environment

- Use the Multipass helper from the repository root to create a disposable VM:

  ```bash
  bash tests/vm/run.sh 24.04
  ```

- Use `22.04` instead of `24.04` when validating the older supported Ubuntu
  release.
- The helper uses official Ubuntu Multipass images, installs GNOME Desktop and
  RDP access, copies a clean snapshot of this repository into the guest, and
  prints the VM address, username, and generated password.
- Connect to the printed RDP address and open a GNOME Terminal in the VM.
- Delete the VM after the run:

  ```bash
  bash tests/vm/run.sh --delete 24.04
  ```

Official Ubuntu Desktop ISOs are available from `releases.ubuntu.com`, but this
runbook uses Multipass images plus desktop bootstrap so the setup can be created
without automating an interactive installer. Third-party prebuilt desktop VM
appliances are intentionally not used for trust and reproducibility.

## Test Steps

1. Go to the copied repository in the VM:

   ```bash
   cd /home/ubuntu/ubuntu_dev_setup
   ```

2. Run the desktop customization path:

   ```bash
   ansible-playbook setup.yml --tags gnome-customization,kitty
   ```

3. Verify GNOME keybindings:

   ```bash
   gsettings get org.gnome.desktop.wm.keybindings switch-to-workspace-left
   gsettings get org.gnome.desktop.wm.keybindings switch-to-workspace-right
   gsettings get org.gnome.desktop.wm.keybindings move-to-workspace-left
   gsettings get org.gnome.desktop.wm.keybindings move-to-workspace-right
   ```

   Expected values:

   - `['<Primary><Alt>h']`
   - `['<Primary><Alt>l']`
   - `['<Primary><Shift><Alt>h']`
   - `['<Primary><Shift><Alt>l']`

4. Verify appearance and input settings:

   ```bash
   gsettings get org.gnome.desktop.input-sources xkb-options
   gsettings get org.gnome.desktop.interface color-scheme
   gsettings get org.gnome.desktop.default-applications.terminal exec
   ```

   Expected values:

   - input options include `caps:escape`
   - color scheme is `prefer-dark`
   - terminal executable points to `~/.local/bin/kitty`

5. Verify workspace indicator extension state:

   ```bash
   gnome-extensions list --enabled | grep workspace-indicator
   ```

6. Run the same playbook command a second time and inspect the recap. Any
   repeated changes should be investigated before declaring the desktop path
   idempotent.

## Pass Criteria

- All expected `gsettings` values are present.
- The workspace indicator extension is enabled.
- Kitty is available as the configured default terminal.
- Re-running the desktop tags does not repeatedly change tasks without a known
  reason.
