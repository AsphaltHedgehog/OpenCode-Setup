#!/usr/bin/env bash
# Open opencode with this harness.
#
#   launch/oc.command                      open opencode in this folder; when this folder is outside
#                                          the private workspace, or when double-clicked, pick a project
#   launch/oc.command <folder> [args...]   open opencode in <folder>, passing args to opencode
#
# The global layer applies everywhere and private/ applies inside its workspace, once install.sh
# has linked them; this runs install.sh first if the links are missing. Projects are found, not
# listed: every git repository or worktree directly in the workspace can be picked.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
dest="${XDG_CONFIG_HOME:-$HOME/.config}/opencode"
workspace=""
if [[ -f $repo/private/.workspace ]]; then workspace="$(cat "$repo/private/.workspace")"; fi

installed=1
if [[ $(readlink "$dest/opencode.jsonc" || true) != "$repo/opencode/opencode.jsonc" ]]; then installed=0; fi
if [[ -n $workspace && $(readlink "$workspace/.opencode" || true) != "$repo/private/opencode" ]]; then installed=0; fi
if (( ! installed )); then "$repo/install.sh" || exit 1; fi

target=""
if [[ $# -gt 0 && -d $1 ]]; then
  target="$(cd "$1" && pwd -P)"
  shift
elif [[ -z $workspace || $PWD == "$workspace"/* ]]; then
  target="$PWD"
else
  projects=()
  for dir in "$workspace"/*/; do
    dir="${dir%/}"
    if [[ -e $dir/.git ]]; then projects+=("${dir##*/}"); fi
  done
  if (( ${#projects[@]} == 0 )); then echo "No git repositories found in $workspace." >&2; exit 1; fi
  PS3="Open opencode in which project? "
  select name in "${projects[@]}"; do
    if [[ -n ${name:-} ]]; then target="$workspace/$name"; break; fi
  done
  if [[ -z $target ]]; then exit 1; fi
fi

if [[ -n $workspace && $target != "$workspace"/* ]]; then
  echo "Note: $target is outside $workspace, so only the global layer applies." >&2
fi
cd "$target"
exec opencode "$@"
