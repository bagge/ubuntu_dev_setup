#!/usr/bin/env bash

_devenv_prepend_path() {
  local entry="$1"
  local old_path="${PATH:-}"
  local new_path="${entry}"
  local path_parts=()
  local part

  # Split the current PATH into entries, then rebuild it after the requested
  # entry. Matching entries are skipped, so this removes duplicates of entry
  # from the old PATH before placing one copy at the beginning.
  IFS=: read -r -a path_parts <<< "${old_path}"
  for part in "${path_parts[@]}"; do
    [[ -n "${part}" && "${part}" != "${entry}" ]] || continue
    new_path="${new_path}:${part}"
  done

  PATH="${new_path}"
}

_devenv_prepend_path "${HOME}/.local/bin"
_devenv_prepend_path "${HOME}/.local/opt/git-current/bin"
unset -f _devenv_prepend_path
export PATH
