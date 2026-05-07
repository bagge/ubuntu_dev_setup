Setup dev environment on Ubuntu and macOS
=========================================
<p>
    <img src="https://img.shields.io/github/license/bagge/ubuntu_dev_setup" hspace="5" >
    <img src="https://github.com/bagge/ubuntu_dev_setup/actions/workflows/ci.yml/badge.svg?event=push" hspace="5" >
</p>

This project contains an ansible playbook to setup a clean Ubuntu or Apple
Silicon macOS installation with my preferred tools and configurations.

In addition there is a script to create a tar file of files to transfer to
a new machine when changing computers.

The playbook is executed with the following command:

```bash
$ ansible-playbook setup.yml
```

The default setup includes Docker, Google Chrome, and Omnissa Horizon Client on
supported platforms. For a lighter install, disable them independently:

```bash
$ ansible-playbook setup.yml --extra-vars install_docker=false
$ ansible-playbook setup.yml --extra-vars "install_docker=false install_google_chrome=false install_omnissa_horizon=false"
```

Dotfile links are guarded by default. If an unmanaged target such as `.bashrc`
already exists, the playbook fails instead of replacing it. To allow replacement
after reviewing the file, run:

```bash
$ ansible-playbook setup.yml --extra-vars replace_existing_dotfiles=true
```

Replaced files are backed up as `<path>.backup.<timestamp>` by default. Disable
that backup with:

```bash
$ ansible-playbook setup.yml --extra-vars "replace_existing_dotfiles=true backup_existing_dotfiles=false"
```

Supported platforms:
- Ubuntu on amd64
- macOS on Apple Silicon

On macOS, Homebrew is installed automatically when it is missing. The default
Homebrew prefix is `/opt/homebrew`.

## Testing

The repository includes a containerized test harness so playbook changes can be
tested without changing the local workstation setup.

Run the default Ubuntu 24.04 container test:

```bash
$ bash tests/container/run.sh
```

Run a specific Ubuntu version:

```bash
$ bash tests/container/run.sh 22.04
```

The container test copies the repository into a disposable container, runs the
playbook, verifies expected state with Ansible assertions, runs the playbook a
second time, and fails unless the second run reports `changed=0` and `failed=0`.

Desktop-specific GNOME behavior should be tested in a disposable Ubuntu Desktop
VM. Create a Multipass-backed Ubuntu 24.04 GNOME VM with:

```bash
$ bash tests/vm/run.sh
```

Create a VM for another supported Ubuntu release with:

```bash
$ bash tests/vm/run.sh 22.04
```

The VM helper uses official Ubuntu Multipass images, installs the GNOME desktop
and RDP access, copies a clean snapshot of this repository into the guest, and
prints the login details plus the next commands to run. It intentionally does
not mount the host checkout, so desktop test runs cannot change the local
workstation setup or the local repository. Use `tests/manual/gnome-vm.md` for
the manual pass/fail checklist.
On headless or non-GNOME Ubuntu hosts, GNOME-only customization tasks are
skipped automatically with a clear message.

Run the macOS Apple Silicon integration test directly on a macOS host:

```bash
$ bash tests/macos/run.sh
```

The macOS test uses the local host rather than Docker because macOS cannot be
run in the Ubuntu container harness. GitHub Actions runs the same test on an
ephemeral Apple Silicon macOS runner.

## Updating pinned tool versions

Pinned tool versions and download checksums live in `group_vars/all`. To check
whether newer upstream versions or checksum refreshes are available, run:

```bash
$ python3 tools/sync_versions.py --check
```

To update the automatic pins and their checksums in `group_vars/all`, run:

```bash
$ python3 tools/sync_versions.py --write
```

The updater uses GitHub, Go, Node.js, and kernel.org Git release metadata and
verifies expected release assets before accepting a new version. If
`GITHUB_TOKEN` is set it will be used for GitHub API requests. For currently
pinned versions, checksum-only refreshes can be done without changing versions:

```bash
$ python3 tools/sync_versions.py --write-current-checksums
```

Omnissa Horizon Client is included in the report as a manual pin because the
vendor download page does not provide a stable version API, but the declared
package URL is still pinned by checksum. Homebrew formulae and casks are not
pinned here; Homebrew resolves those versions during installation. GitHub CLI
is installed from pinned GitHub release archives on both Ubuntu and macOS.

On Ubuntu, Git is built from the pinned kernel.org source tarball and installed
under `~/.local/opt/git-<version>`. The active install is exposed through
`~/.local/opt/git-current`, which is prepended to `PATH` for interactive shells.
apt Git remains installed as a bootstrap/build dependency. To remove the
source-built Git install, delete `~/.local/opt/git-current` and any
`~/.local/opt/git-*` directories.

nvm is installed from the pinned `nvm_version` installer script after verifying
`nvm_install_checksum`. The default Node.js version is controlled by
`node_major_version`.

## Transfer bundle

Create a transfer archive from selected local dotfiles, credentials, SSH
configuration, and browser bookmarks with:

```bash
$ ./create_bundle.sh
```

The script writes `sensitive-transfer-bundle.tar.gz` in the current directory.
The archive contains secrets and is not encrypted, so store and move it
carefully. Missing optional paths are skipped with warnings.

Other things to remember to transfer when changing computers:
- Stored passwords in chrome

On the new machine, remember to do the following manually:
- Import stored passwords in chrome
- Untar `sensitive-transfer-bundle.tar.gz` in the home directory
- Start neovim to have lazy download all plugins
- Authenticate Copilot in neovim

TODO:
- Add kitty icat command to show bazel deps in terminal

## Tools

Currently the following tools are installed and setup:
- Bash-it
  - With powerline-multiline theme and gitstatus plugin
- Kitty
- Neovim
- Ranger
- Fzf with git extensions integrated in bash and also used in neovim via
  FzfLua.
- bat
- glow
- mdcat

Additionally my neovim configuration will be fetched and setup which contains
my preferred plugins.

The main idea of this setup is to have a tiling environment without requiring
tmux or a tiling window manager.
This is achieved by using kitty as the terminal.
Though in addition configuration is done to have consistent keybindings for
movement between neovim windows and kitty windows. On Ubuntu, GNOME keybindings
are modified to use easier to reach (more vim like) keybindings to switch
workspaces and to move windows between workspaces. On macOS, safe desktop
defaults such as dark mode and Caps Lock to Escape are configured, while
workspace keybindings remain manual because macOS stores them in a brittle
system preference structure. See `playbooks/gnome-customization.yml` for more
details.

## Keybindings

These are the customized keybindings on top of the defaults. 

### Gnome shell

| Keybinding       | Description                                       |
| ---------------- | ------------------------------------------------- |
| ctrl-alt-h       | Switch workspace to the left                      |
| ctrl-alt-l       | Switch workspace to the right                     |
| shift-ctrl-alt-h | Move current window to the workspace to the left  |
| shift-ctrl-alt-l | Move current window to the workspace to the right |

### Kitty + Neovim

#### Movements
The configurations sets up integration between Kitty and Neovim in order to have
the same keybindings when:
- Moving between kitty windows
- Moving between Neovim windows
- Moving between kitty windows and neovim windows
Same similarity is achieved for resizing of windows

| Keybinding       | Description                                       |
| ---------------- | ------------------------------------------------- |
| ctrl-{h,j,k,l}   | Switch to window to {left, down, up, right}       |
| alt-{h,j,k,l}    | Resize current window to {left, down, up, right}  |

#### Scrollback

The configuration sets up a plugin that allows loading parts of the scrollback
into a new neovim instance started in the terminal where the scrollback can be processed
using neovim. Once processed one can choose to execute the lines in the buffer, copy them
to clipboard and a few other options.

| Keybinding       | Description                                                |
| ---------------- | ---------------------------------------------------------- |
| shift-ctrl-z     | Scroll up to next prompt in scrollback                     |
| shift-ctrl-x     | Scroll down to next prompt in scrollback                   |
| shift-ctrl-a     | Load the output of the last command into neovim            |
| shift-ctrl-g     | Load the output of the last scrolled to prompt into neovim |
| shift-ctrl-s     | Load the entire scrollback into neovim (could be slow...)  |

## Neovim

See [nvim-config](https://github.com/bagge/nvim-config).

## Kitty

| Keybinding       | Description                     |
| ---------------- | ------------------------------- |
| shift-ctrl-enter | Open new window                 |
| shift-ctrl-t     | Create new tab                  |
| shift-ctrl-alt-t | Rename tab                      |
| shift-ctrl-{h,l} | Switch tab to {left, right}     |
| shift-ctrl-{c,v} | {Copy to, Paste from} clipboard |
| shift-ctrl-{j,k} | Scroll {down, up}               |

### Window layouts

The default layout is tall (i.e. one full window to left, all other windows horizontally
split in the right column). The other enabled layouts are stack and splits.

| Keybinding   | Description                                                                   |
| ------------ | ----------------------------------------------------------------------------- |
| shift-ctrl-m | Toggle layout stack                                                           |
| shift-ctrl-n | Switch to next layout                                                         |
| shift-ctrl-y | Split current window horizontally or vertically (only valid in layout splits) |
| shift-ctrl-o | Split current window horizontally (only valid in layout splits)               |
| shift-ctrl-i | Split current window vertically (only valid in layout splits)                 |

### Copy with hints

This is a really useful feature in Kitty. By acivating one of the modes below hints will be added
to regexp matched content in the visible scrollback. By pressing the key in the hint the matched
content is copied to the command line at the current cursor location. Some keybindings have been
set up to open the matched hint in an external program.

| Keybinding        | Description                                                                   |
| ----------------- | ------------------------------------------- |
| shift-ctrl-p -> f | Match paths, copy selected to command line  |
| shift-ctrl-p -> F | Open matched path with default program      |
| shift-ctrl-p -> l | Match lines, copy selected to command line  |
| shift-ctrl-p -> w | Match words, copy selected to command line  |
| shift-ctrl-p -> h | Match hashes, copy selected to command line |
| shift-ctrl-e      | Match URLs, open selected in browser        |

### Special keybindings

Some other semi-useful keybindings that don't fit elsewhere.

| Keybinding     | Description                                   |
| -------------- | --------------------------------------------- |
| shift-ctrl-esc | Open a kitty-shell                            |
| shift-ctrl-F5  | Reload kitty.conf                             |
| shift-ctrl-F2  | Edit kitty.conf                               |
| shift-ctrl-F6  | Debug configuration                           |
| ctrl-'         | Output ~ (original key is broken on keyboard) |
| shift-ctrl-'   | Output ^ (original key is broken on keyboard) |

## Customizations

<details>
<summary>Overview of gnome customizations</summary>
    <ul>
    <li>Enable extension workspace indicator</li>
    <li>Change caps-lock key to be another escape key</li>
    <li>Set dark mode</li>
    <li>Set default terminal to Kitty</li>
    </ul>
</details>

<details>
<summary>Overview of Kitty configuration</summary>
    <ul>
    <li>Have launchers and icons properly set up in the desktop environment</li>
    <li>Uses the Hack nerdfont</li>
    <li>Uses theme Dracula</li>
    <li>Set up plugin kitty_scrollback to enable integration between scrollback and Neovim</li>
    <li>Attempts to set up sensible keybindings see keybindings-section for details</li>
    <li>Some minimal theming of kitty to have a small border to show the active window</li>
    </ul>    
</details>

<details>
<summary>Overview of ranger configuration</summary>
    <ul>
    <li>Enable preview directly in the kitty terminal</li>
    </ul>
</details>
