# Manual GNOME VM Test Runbook

Use this runbook for desktop behavior that cannot be validated reliably in a
container or a headless GitHub Actions runner.

## Environment

- Use the Multipass helper from the repository root to create a disposable VM:

  ```bash
  bash tests/vm/run.sh 26.04
  ```

- Use `22.04` or `24.04` when validating an older supported Ubuntu release.
- The helper uses official Ubuntu Multipass images, installs GNOME Desktop and
  RDP access, copies a clean snapshot of this repository into the guest, and
  prints the VM address, username, and generated password.
- Ubuntu 26.04 uses GNOME Remote Desktop on port 3389. Accept the self-signed TLS
  certificate created for the disposable VM when the RDP client prompts.
- Ubuntu 22.04 and 24.04 continue to use xrdp on the same port.
- Connect to the printed RDP address and open a GNOME Terminal in the VM.
- Delete the VM after the run:

  ```bash
  bash tests/vm/run.sh --delete 26.04
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

3. On Ubuntu 26.04, verify the RDP desktop is a Wayland GNOME session:

   ```bash
   printf 'session=%s wayland=%s\n' "$XDG_SESSION_TYPE" "$WAYLAND_DISPLAY"
   ```

   Expected: `session=wayland` and a non-empty Wayland display. On older
   releases, the xrdp session may report `x11` instead.

4. Verify GNOME keybindings:

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

5. Verify appearance and input settings:

   ```bash
   gsettings get org.gnome.desktop.input-sources xkb-options
   gsettings get org.gnome.desktop.interface color-scheme
   gsettings get org.gnome.desktop.default-applications.terminal exec
   ```

   Expected values:

   - input options include `caps:escape`
   - color scheme is `prefer-dark`
   - terminal executable points to `~/.local/bin/kitty`

6. Verify workspace indicator extension state:

   ```bash
   gnome-extensions list --enabled | grep workspace-indicator
   ```

7. Run the same playbook command a second time and inspect the recap. Any
   repeated changes should be investigated before declaring the desktop path
   idempotent.

## Pass Criteria

- All expected `gsettings` values are present.
- The workspace indicator extension is enabled.
- Kitty is available as the configured default terminal.
- Ubuntu 26.04 is detected as a usable Wayland GNOME session.
- Re-running the desktop tags does not repeatedly change tasks without a known
  reason.
