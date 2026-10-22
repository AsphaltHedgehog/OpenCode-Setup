#!/usr/bin/env python3
"""Tests for spec_trace.py. Each case builds a small git repo and compares the problems the script
reports with the list worked out by hand from the files below. Run: python3 test_spec_trace.py"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).with_name("spec_trace.py")

SPEC_12 = """# SPEC-12 Orders: limit parameter

State: implemented
Created: 2026-10-22 · Updated: 2026-10-22

## Acceptance criteria
- AC-1 Without `limit`, 20 orders come back.
- AC-2 `limit=101` returns 400 with code `invalid_limit`.
"""


def repo_with(files, commits=None):
    """A git repo holding files; commits is a list of (unix time, [paths]) committed in order."""
    root = pathlib.Path(tempfile.mkdtemp())
    run = lambda *a, **env: subprocess.run(["git", "-C", str(root), *a], check=True, capture_output=True,
                                           env={**os.environ, **env})
    run("init", "-q", "-b", "main")
    run("config", "user.name", "t")
    run("config", "user.email", "t@example.invalid")
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    for when, paths in commits or [(1_700_000_000, list(files))]:
        run("add", *paths)
        stamp = f"@{when} +0000"
        run("commit", "-q", "-m", "c", GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
    return root


def trace(root):
    out = subprocess.run([sys.executable, str(SCRIPT), str(root), "--json"], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


class Trace(unittest.TestCase):
    def test_clean_spec_has_no_problems(self):
        root = repo_with({
            "docs/specs/orders-limit-SPEC-12.md": SPEC_12,
            "api.py": "# spec: SPEC-12\ndef parse_limit(raw):\n    pass\n",
            "tests/test_api.py": "# spec: SPEC-12/AC-1\n# spec: SPEC-12/AC-2\n",
        })
        result = trace(root)
        self.assertEqual(result["problems"], [])
        spec = result["specs"][0]
        self.assertEqual((spec["id"], spec["state"], spec["criteria"]), ("SPEC-12", "implemented", ["AC-1", "AC-2"]))
        self.assertEqual(spec["code"], ["api.py:1"])
        self.assertEqual(spec["tests"], {"AC-1": ["tests/test_api.py:1"], "AC-2": ["tests/test_api.py:2"]})

    def test_every_kind_of_problem(self):
        root = repo_with({
            "docs/specs/orders-limit-SPEC-12.md": SPEC_12,                      # AC-2 untested below
            "docs/specs/refunds-SPEC-13.md": "# SPEC-13 Refunds\n\nState: approved\n",       # no code
            "docs/specs/old-name-SPEC-99.md": "# SPEC-14 Wrong file name\n\nState: draft\n",
            "docs/specs/a-SPEC-18.md": "# SPEC-18 One\n\nState: draft\n",
            "docs/specs/b-SPEC-18.md": "# SPEC-18 Two\n\nState: draft\n",   # duplicate ID
            "docs/specs/legacy-SPEC-15.md": "# SPEC-15 Legacy\n\nState: deprecated\n",
            "docs/specs/no-state-SPEC-16.md": "# SPEC-16 No state\n",
            "docs/specs/notes.md": "Some notes without a heading ID\n",
            "docs/specs/draft-SPEC-17.md": "# SPEC-17 Draft\n\nState: draft\n",
            "api.py": "# spec: SPEC-12\n# spec: SPEC-404\n# spec: SPEC-15\n# spec: SPEC-17\n",
            "tests/test_api.py": "# spec: SPEC-12/AC-1\n# spec: SPEC-12/AC-9\n",
        })
        self.assertEqual(sorted(trace(root)["problems"]), sorted([
            "docs/specs/b-SPEC-18.md: duplicate ID SPEC-18, also in docs/specs/a-SPEC-18.md",
            "docs/specs/notes.md: first line is not '# <ID> <title>'",
            "docs/specs/old-name-SPEC-99.md: file name should end in -SPEC-14.md",
            "docs/specs/no-state-SPEC-16.md: no 'State:' line",
            "api.py:2: tag points to unknown spec SPEC-404",
            "api.py:3: tag points to deprecated spec SPEC-15",
            "tests/test_api.py:2: SPEC-12 has no AC-9",
            "SPEC-12: implemented but no test tags AC-2",
            "SPEC-13: approved but no code carries 'spec: SPEC-13'",
            "SPEC-17: still draft, but code already implements it",
        ]))

    def test_spec_changed_after_its_code(self):
        files = {
            "api.py": "# spec: SPEC-12\n",
            "tests/test_api.py": "# spec: SPEC-12/AC-1\n# spec: SPEC-12/AC-2\n",
            "docs/specs/orders-limit-SPEC-12.md": SPEC_12,
        }
        root = repo_with(files, commits=[(1_700_000_000, ["api.py", "tests/test_api.py"]),
                                         (1_700_086_400, ["docs/specs/orders-limit-SPEC-12.md"])])
        self.assertEqual(trace(root)["problems"], ["SPEC-12: the spec changed after its code; check the code still matches"])

    def test_strict_exit_code(self):
        root = repo_with({"docs/specs/refunds-SPEC-13.md": "# SPEC-13 Refunds\n\nState: approved\n"})
        run = lambda *a: subprocess.run([sys.executable, str(SCRIPT), str(root), *a], capture_output=True).returncode
        self.assertEqual((run(), run("--strict")), (0, 1))


if __name__ == "__main__":
    unittest.main()
