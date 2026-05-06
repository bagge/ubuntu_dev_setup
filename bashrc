#!/usr/bin/env bash

# If not running interactively, don't do anything
case $- in
  *i*) ;;
    *) return;;
esac


export PATH="${HOME}/.local/opt/git-current/bin:${HOME}/.local/bin:${HOME}/bin:${HOME}/go/bin:${PATH}"
export MANPATH="${MANPATH}:${HOME}/.local/share/man"

# Load customizations
for f in "${HOME}"/.bashrc.d/enabled/*; do
  [ -e "${f}" ] || continue
  # shellcheck source=/dev/null
  source "${f}"
done
