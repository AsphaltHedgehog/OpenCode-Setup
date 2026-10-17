#!/usr/bin/env bash
# Link this setup into opencode's global config folder, so that every project gets it.
#
#   ./install.sh              link opencode.jsonc and each agent, command and skill
#   ./install.sh --dry-run    show what would change, change nothing
#   ./install.sh --uninstall  remove the links that point into this repo
#
# Only symlinks are made or removed. A file that isn't a link into this repo is never replaced,
# so your own opencode.json, agents, commands and skills stay as they are.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
src="$repo/opencode"
dest="${XDG_CONFIG_HOME:-$HOME/.config}/opencode"
mode=install
dry=0

for arg in "$@"; do
  case "$arg" in
    --dry-run) dry=1 ;;
    --uninstall) mode=uninstall ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "unknown option: $arg (see --help)" >&2; exit 2 ;;
  esac
done

act() {  # act <link|remove> <what> <command...>: run the command, or only say it on a dry run
  local verb="$1" what="$2"; shift 2
  if (( dry )); then echo "would $verb $what"; return; fi
  "$@"
  case "$verb" in link) echo "linked  $what" ;; remove) echo "removed $what" ;; esac
}

items() {  # paths relative to opencode/: the config file, then each agent, command and skill
  echo opencode.jsonc
  local f
  for f in "$src"/agents/*.md "$src"/commands/*.md "$src"/skills/*/; do
    if [[ -e $f ]]; then f="${f%/}"; echo "${f#"$src"/}"; fi
  done
}

stale() {  # links into this repo whose target is gone, such as a skill that was renamed
  local link
  find "$dest" -maxdepth 2 -type l 2>/dev/null | while IFS= read -r link; do
    if [[ $(readlink "$link") == "$src/"* && ! -e $link ]]; then echo "$link"; fi
  done
}

status=0

while IFS= read -r link; do
  act remove "stale link $link" rm "$link"
done < <(stale)

while IFS= read -r rel; do
  from="$src/$rel"
  to="$dest/$rel"
  if [[ $mode == uninstall ]]; then
    if [[ -L $to && $(readlink "$to") == "$from" ]]; then act remove "$to" rm "$to"; fi
    continue
  fi
  if [[ -L $to && $(readlink "$to") == "$from" ]]; then echo "ok      $to"; continue; fi
  if [[ -e $to || -L $to ]]; then
    echo "SKIP    $to already exists and is not a link into this repo" >&2
    status=1
    continue
  fi
  if (( ! dry )); then mkdir -p "$(dirname "$to")"; fi
  act link "$to -> $from" ln -s "$from" "$to"
done < <(items)

if [[ $mode == install ]] && (( ! dry )); then
  echo
  echo "Next: run 'python3 scripts/check.py', then open opencode and type /qa or press Tab to find the qa agent."
fi
exit "$status"
