#!/usr/bin/env bash
# Link this harness into place. Only symlinks are made or removed, and a file that isn't one of
# this repo's links is never replaced, so your own config stays as it is.
#
#   ./install.sh                         link the global layer, opencode/, into ~/.config/opencode,
#                                        and private/ into its workspace if one was set before
#   ./install.sh --private-to <folder>   set <folder> as the workspace for private/ and link it as
#                                        <folder>/.opencode and <folder>/AGENTS.md, which every
#                                        project under <folder> picks up
#   ./install.sh --dry-run               show what would change, change nothing
#   ./install.sh --uninstall             remove every link that points into this repo
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
src="$repo/opencode"
private="$repo/private"
dest="${XDG_CONFIG_HOME:-$HOME/.config}/opencode"
mode=install
dry=0
workspace=""

while (( $# )); do
  case "$1" in
    --dry-run) dry=1 ;;
    --uninstall) mode=uninstall ;;
    --private-to)
      if [[ $# -lt 2 || ! -d $2 ]]; then echo "--private-to needs an existing folder" >&2; exit 2; fi
      workspace="$(cd "$2" && pwd -P)"
      shift ;;
    -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
    *) echo "unknown option: $1 (see --help)" >&2; exit 2 ;;
  esac
  shift
done

if [[ -n $workspace ]]; then
  if [[ ! -d $private ]]; then echo "There is no private/ folder to link." >&2; exit 2; fi
  if (( ! dry )); then echo "$workspace" > "$private/.workspace"; fi
elif [[ -f $private/.workspace ]]; then
  workspace="$(cat "$private/.workspace")"
fi

act() {  # act <link|remove> <what> <command...>: run the command, or only say it on a dry run
  local verb="$1" what="$2"; shift 2
  if (( dry )); then echo "would $verb $what"; return; fi
  "$@"
  case "$verb" in link) echo "linked  $what" ;; remove) echo "removed $what" ;; esac
}

pairs() {  # every link this repo owns, as "<target><TAB><link>"
  local f
  printf '%s\t%s\n' "$src/opencode.jsonc" "$dest/opencode.jsonc"
  if [[ -f $src/AGENTS.md ]]; then printf '%s\t%s\n' "$src/AGENTS.md" "$dest/AGENTS.md"; fi
  for f in "$src"/agents/*.md "$src"/commands/*.md "$src"/skills/*/; do
    if [[ -e $f ]]; then f="${f%/}"; printf '%s\t%s\n' "$f" "$dest/${f#"$src"/}"; fi
  done
  if [[ -n $workspace ]]; then
    if [[ -d $private/opencode ]]; then printf '%s\t%s\n' "$private/opencode" "$workspace/.opencode"; fi
    if [[ -f $private/AGENTS.md ]]; then printf '%s\t%s\n' "$private/AGENTS.md" "$workspace/AGENTS.md"; fi
  fi
}

stale() {  # links into this repo whose target is gone, such as a skill that was renamed
  local link
  {
    find "$dest" -maxdepth 2 -type l 2>/dev/null
    if [[ -n $workspace ]]; then find "$workspace" -maxdepth 1 -type l 2>/dev/null; fi
  } | while IFS= read -r link; do
    if [[ $(readlink "$link") == "$repo/"* && ! -e $link ]]; then echo "$link"; fi
  done
}

status=0

while IFS= read -r link; do
  act remove "stale link $link" rm "$link"
done < <(stale)

while IFS=$'\t' read -r from to; do
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
done < <(pairs)

if [[ $mode == install ]] && (( ! dry )); then
  echo
  echo "Next: run 'python3 scripts/check.py', then 'launch/oc.command' to open opencode with the harness."
fi
exit "$status"
