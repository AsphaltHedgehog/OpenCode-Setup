#!/usr/bin/env python3
"""Trace spec items to code and tests by ID, never by file path.

Spec items live in docs/specs/, one markdown file each, named <task-slug>-<ID>.md, whose first
line is "# <ID> <title>" and which carry a "State:" line and "- AC-<n>" acceptance criteria.
Code carries "spec: <ID>" and tests carry "spec: <ID>/AC-<n>", in a comment or a test name.

    python3 spec_trace.py [repo]           report, exit 0
    python3 spec_trace.py [repo] --strict  report, exit 1 when there are problems
    python3 spec_trace.py [repo] --json    the same as JSON
"""
import json
import pathlib
import re
import subprocess
import sys

ID = r"[A-Z][A-Z0-9]*-\d+"
HEADING = re.compile(rf"^#\s+({ID})\b\s*(.*)$")
STATE = re.compile(r"^State:\s*(draft|approved|implemented|deprecated)\b", re.I | re.M)
CRITERION = re.compile(r"^\s*[-*]\s*\**(AC-\d+)\b", re.M)
TAG = re.compile(rf"spec:\s*({ID})(?:/(AC-\d+))?")
FILE_ID = re.compile(rf"-({ID})\.md$")
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec)/|(^|/)test_[^/]*$|_test\.[a-z]+$|\.(test|spec)\.[a-z]+$")


def git(repo, *args):
    run = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return run.stdout if run.returncode == 0 else ""


def last_change(repo, path):
    """Unix time of the last commit that touched path, or None if it was never committed."""
    out = git(repo, "log", "-1", "--format=%ct", "--", path).strip()
    return int(out) if out else None


def read_specs(repo):
    specs, problems = {}, []
    folder = repo / "docs" / "specs"
    for path in sorted(folder.glob("*.md")) if folder.is_dir() else []:
        if path.name.lower() == "readme.md":
            continue
        rel = str(path.relative_to(repo))
        text = path.read_text(encoding="utf-8", errors="replace")
        first = text.splitlines()[0] if text else ""
        m = HEADING.match(first)
        if not m:
            problems.append(f"{rel}: first line is not '# <ID> <title>'")
            continue
        sid, title = m.group(1), m.group(2).strip()
        named = FILE_ID.search(path.name)
        if not named or named.group(1) != sid:
            problems.append(f"{rel}: file name should end in -{sid}.md")
        if sid in specs:
            problems.append(f"{rel}: duplicate ID {sid}, also in {specs[sid]['file']}")
            continue
        state = STATE.search(text)
        specs[sid] = {"id": sid, "title": title, "file": rel,
                      "state": state.group(1).lower() if state else "unknown",
                      "criteria": sorted(set(CRITERION.findall(text)), key=lambda c: int(c[3:])),
                      "code": [], "tests": {}}
        if not state:
            problems.append(f"{rel}: no 'State:' line")
    return specs, problems


def read_tags(repo, specs):
    tags, problems = [], []
    files = [f for f in git(repo, "ls-files").splitlines() if not f.startswith("docs/specs/")]
    for f in files:
        path = repo / f
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for m in TAG.finditer(line):
                tags.append((m.group(1), m.group(2), f, n))
    for sid, crit, f, n in tags:
        where = f"{f}:{n}"
        spec = specs.get(sid)
        if spec is None:
            problems.append(f"{where}: tag points to unknown spec {sid}")
            continue
        if spec["state"] == "deprecated":
            problems.append(f"{where}: tag points to deprecated spec {sid}")
        if TEST_PATH.search(f):
            spec["tests"].setdefault(crit or "*", []).append(where)
        else:
            spec["code"].append(where)
        if crit and crit not in spec["criteria"]:
            problems.append(f"{where}: {sid} has no {crit}")
    return problems


def check_specs(repo, specs):
    problems = []
    for sid, s in specs.items():
        if s["state"] in ("approved", "implemented") and not s["code"]:
            problems.append(f"{sid}: {s['state']} but no code carries 'spec: {sid}'")
        if s["state"] == "implemented":
            untested = [c for c in s["criteria"] if c not in s["tests"]]
            if untested:
                problems.append(f"{sid}: implemented but no test tags {', '.join(untested)}")
        if s["state"] == "draft" and s["code"]:
            problems.append(f"{sid}: still draft, but code already implements it")
        spec_time = last_change(repo, s["file"])
        code_files = {w.rsplit(":", 1)[0] for w in s["code"]}
        code_times = [t for t in (last_change(repo, f) for f in code_files) if t]
        if spec_time and code_times and spec_time > max(code_times):
            problems.append(f"{sid}: the spec changed after its code; check the code still matches")
    return problems


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    repo = pathlib.Path(args[0] if args else ".").resolve()
    specs, problems = read_specs(repo)
    problems += read_tags(repo, specs)
    problems += check_specs(repo, specs)
    if "--json" in sys.argv:
        print(json.dumps({"specs": list(specs.values()), "problems": problems}, indent=1))
    else:
        if not specs:
            print("No spec items in docs/specs/.")
        for s in specs.values():
            tested = sum(1 for c in s["criteria"] if c in s["tests"])
            print(f"{s['id']:<10} {s['state']:<12} code {len(s['code']):>2}  tests {tested}/{len(s['criteria'])} AC  {s['title']}")
        print()
        print(f"{len(problems)} problem(s)" + (":" if problems else "."))
        for p in problems:
            print(f"  {p}")
    sys.exit(1 if problems and "--strict" in sys.argv else 0)


if __name__ == "__main__":
    main()
