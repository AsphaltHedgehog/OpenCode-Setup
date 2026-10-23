#!/usr/bin/env python3
"""Print the sprint swarm's limits for a project, as JSON.

The numbers are upper limits, not quotas. The lead starts only as many agents as the work needs,
never more than a role's limit, and skips a role whose limit is 0.

Sources, lowest precedence first. Each one replaces only the keys it sets:
  1. swarm.defaults.json in this skill's folder (the harness defaults)
  2. this machine's file: ~/.config/opencode/swarm.json (or $XDG_CONFIG_HOME/opencode/swarm.json)
  3. every .opencode/swarm.json from the home folder down to the project, the nearest last

    python3 swarm_limits.py [project]
"""
import json
import os
import pathlib
import subprocess
import sys

SKILL = pathlib.Path(__file__).resolve().parent.parent
ROLES = ("design", "dev", "qa", "eval")


def merge(base, extra):
    out = dict(base)
    for key, value in extra.items():
        out[key] = merge(out[key], value) if isinstance(value, dict) and isinstance(out.get(key), dict) else value
    return out


def sources(project):
    machine = pathlib.Path(os.environ.get("XDG_CONFIG_HOME") or pathlib.Path.home() / ".config") / "opencode" / "swarm.json"
    chain, home = [], pathlib.Path.home().resolve()
    for folder in (project, *project.parents):
        chain.append(folder / ".opencode" / "swarm.json")
        if folder == home:
            break
    candidates = [SKILL / "swarm.defaults.json", machine, *reversed(chain)]
    seen, found = set(), []
    for path in candidates:
        real = path.resolve() if path.exists() else path
        if path.is_file() and real not in seen:
            seen.add(real)
            found.append(path)
    return found


def main():
    project = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    top = subprocess.run(["git", "-C", str(project), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    root = pathlib.Path(top.stdout.strip()) if top.returncode == 0 else project

    limits, used, errors = {}, [], []
    for path in sources(project):
        try:
            limits = merge(limits, json.loads(path.read_text()))
            used.append(str(path))
        except (OSError, ValueError) as e:
            errors.append(f"{path}: {e}")

    roles = limits.get("max", {})
    for role, value in roles.items():
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"max.{role} must be a whole number of 0 or more, not {value!r}")
    rounds = limits.get("qa_rounds", 2)
    if not isinstance(rounds, int) or isinstance(rounds, bool) or rounds < 1:
        errors.append(f"qa_rounds must be a whole number of 1 or more, not {rounds!r}")
    if errors:
        sys.exit("swarm limits are invalid:\n  " + "\n  ".join(errors))

    worktrees = (root / limits.get("worktrees", "../{repo}.worktrees").format(repo=root.name)).resolve()
    print(json.dumps({
        "max": {role: roles.get(role, 0) for role in ROLES},
        "unknown_roles": sorted(set(roles) - set(ROLES)),
        "qa_rounds": rounds,
        "worktrees": str(worktrees),
        "sources": used,
    }, indent=1))


if __name__ == "__main__":
    main()
