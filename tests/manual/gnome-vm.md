# Manual GNOME VM Test Runbook

Use this runbook for desktop behavior that cannot be validated reliably in a
container or a headless GitHub Actions runner.

## Environment

- Start from a clean Ubuntu Desktop VM snapshot.
- Use the same Ubuntu release being validated for the workstation setup.
- Ensure the VM has a normal graphical GNOME session and network access.
- Revert to the clean snapshot after each test run.

## Test Steps

1. Clone this repository in the VM.
2. Install Ansible and required collections:

   ```bash
   sudo apt-get update
   sudo apt-get install -y ansible git
   ansible-galaxy collection install -r requirements.yml
   ```

3. Run the desktop customization path:

   ```bash
   ansible-playbook setup.yml --tags gnome-customization,kitty
   ```

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
- Re-running the desktop tags does not repeatedly change tasks without a known
  reason.
