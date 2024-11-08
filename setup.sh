#!/bin/bash

set -e

BASH_IT_TAG=v3.0.3
FZF_TAG=0.53.0

pushd "$(dirname "$0")"
mkdir -p repos
mkdir -p tarballs

###############################################################################
# Keyboard customization
gsettings set org.gnome.desktop.input-sources xkb-options "['caps:escape']"

gsettings set org.gnome.desktop.wm.keybindings switch-to-workspace-left "['<Primary><Alt>h']"
gsettings set org.gnome.desktop.wm.keybindings switch-to-workspace-right "['<Primary><Alt>l']"
gsettings set org.gnome.desktop.wm.keybindings move-to-workspace-left "['<Primary><Shift><Alt>h']"
gsettings set org.gnome.desktop.wm.keybindings move-to-workspace-right "['<Primary><Shift><Alt>l']"
###############################################################################

###############################################################################
# Bash_it
git clone https://github.com/Bash-it/bash-it.git repos/bash-it
git -C repos/bash-it checkout $BASH_IT_TAG
ln -s repos/bash-it ~/.bash_it
ln -s bash_it.bashrc ~/.bash_it.bashrc
# Enable gitstatus plugin in bash-it
# https://github.com/romkatv/gitstatus?tab=readme-ov-file#using-from-bash
git clone --depth=1 https://github.com/romkatv/gitstatus.git repos/gitstatus
###############################################################################

###############################################################################
# Neovim
wget -P tarballs https://github.com/neovim/neovim/releases/download/nightly/nvim-linux64.tar.gz
tar -C tarballs -zxvf nvim-linux64.tar.gz
ln -s tarballs/nvim-linux64/bin/nvim ~/.local/bin/nvim

git clone https://github.com/bagge/nvim-config.git repos/nvim-config
ln -s repos/nvim-config ~/.config/nvim

# wl-copy and wl-paste as well as ripgrep for neovim
sudo apt install -y wl-clipboard ripgrep
###############################################################################

###############################################################################
# Ranger
sudo apt install -y ranger
mkdir -p ~/.config/ranger
ln -s ranger.conf ~/.config/ranger/rc.conf
###############################################################################


# Install gopls to use lsp in nvim
# TODO: Install gopls as $ go install golang.org/x/tools/gopls@latest
# Add the local go/bin to PATH in .bashrc (that's where gopls ends up)

###############################################################################
# TODO: Install nodejs for copilot
# # installs nvm (Node Version Manager)
# curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.0/install.sh | bash
#
# # download and install Node.js (you may need to restart the terminal)
# nvm install 20
#
# # verifies the right Node.js version is in the environment
# node -v # should print `v20.18.0`
#
# # verifies the right npm version is in the environment
# npm -v # should print `10.8.2`
###############################################################################

###############################################################################
# Install Nerdfont
FONTDIR=~/.local/share/fonts
mkdir -p $FONTDIR
wget -P tarballs https://github.com/ryanoasis/nerd-fonts/releases/download/v3.2.1/Hack.zip
unzip tarballs/Hack.zip -d $FONTDIR
fc-cache -f -v
###############################################################################

###############################################################################
# Kitty installation
curl -L https://sw.kovidgoyal.net/kitty/installer.sh dest=tarballs | sh /dev/stdin
# Create symbolic links to add kitty and kitten to PATH (assuming ~/.local/bin is in
# your system-wide PATH)
ln -s tarballs/kitty.app ~/.local/kitty.app
ln -s ~/.local/kitty.app/bin/kitty ~/.local/kitty.app/bin/kitten ~/.local/bin/
# Place the kitty.desktop file somewhere it can be found by the OS
cp ~/.local/kitty.app/share/applications/kitty.desktop ~/.local/share/applications/
# If you want to open text files and images in kitty via your file manager also add the kitty-open.desktop file
cp ~/.local/kitty.app/share/applications/kitty-open.desktop ~/.local/share/applications/
# Update the paths to the kitty and its icon in the kitty desktop file(s)
sed -i "s|Icon=kitty|Icon=$(readlink -f ~)/.local/kitty.app/share/icons/hicolor/256x256/apps/kitty.png|g" ~/.local/share/applications/kitty*.desktop
sed -i "s|Exec=kitty|Exec=$(readlink -f ~)/.local/kitty.app/bin/kitty|g" ~/.local/share/applications/kitty*.desktop
# Make xdg-terminal-exec (and hence desktop environments that support it use kitty)
echo 'kitty.desktop' > ~/.config/xdg-terminals.list

gsettings set org.gnome.desktop.default-applications.terminal exec "${HOME}/.local/bin/kitty"

# Setup kitty configuration
mkdir -p ~/.config/kitty
ln -s kitty.conf ~/.config/kitty/kitty.conf

git clone https://github.com/yurikhan/kitty_grab.git repos/kitty_grab

# Install kitty_grab
ln -s repos/kitty_grab/grab-vim.conf.example ~/.config/kitty/grab.conf
# echo "map ctrl+w kitten kitty_grab/grab.py" >> ~/.config/kitty/kitty.conf

# Install kitty-themes
git clone https://github.com/kovidgoyal/kitty-themes.git repos/kitty-themes
ln -s repos/kitty-themes/themes/Dracula.conf ~/.config/kitty/theme.conf
###############################################################################

###############################################################################
# Configure kitty-scrollback
# nvim --headless +'KittyScrollbackGenerateKittens' >> ~/.config/kitty/kitty.conf
###############################################################################

###############################################################################
# To get a local gitignore
git config --global core.excludesfile ~/.gitignore
echo "go.sum" > ~/.gitignore
###############################################################################

###############################################################################
# Some additional git configuration
git config core.editor nvim
###############################################################################

###############################################################################
# Build fzf
git clone https://github.com/junegunn/fzf repos/fzf
git -C repos/fzf checkout $FZF_TAG -b ${FZF_TAG}_build
(cd repos/fzf && ./install --no-update-rc)

git clone https://github.com/junegunn/fzf-git.sh repos/fzf-git.sh
#cd fzf-git.sh
#echo ". $PWD/fzf.git.sh" >> ~/.bashrc
#cd ..
# Enable XON/XOFF flow-control to disable CTRL-S freezing the terminal which
# interferes with fzf-git.sh
#echo "stty -ixon" >> ~/.bashrc
###############################################################################


