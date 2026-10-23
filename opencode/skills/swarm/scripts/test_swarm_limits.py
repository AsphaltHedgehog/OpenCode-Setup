#!/usr/bin/env python3
"""Tests for swarm_limits.py, with expected limits worked out by hand from the files each case writes.
Run: python3 test_swarm_limits.py"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).with_name("swarm_limits.py")


class Limits(unittest.TestCase):
    def setUp(self):
        self.home = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.workspace = self.home / "work"
        self.project = self.workspace / "shop"
        self.project.mkdir(parents=True)
        subprocess.run(["git", "-C", str(self.project), "init", "-q"], check=True)

    def write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))

    def limits(self, check=True):
        env = {**os.environ, "HOME": str(self.home), "XDG_CONFIG_HOME": str(self.home / ".config")}
        run = subprocess.run([sys.executable, str(SCRIPT), str(self.project)], capture_output=True, text=True, env=env)
        if check:
            self.assertEqual(run.returncode, 0, run.stderr)
            return json.loads(run.stdout)
        return run

    def test_defaults_only(self):
        result = self.limits()
        self.assertEqual(result["max"], {"design": 1, "dev": 3, "qa": 2, "eval": 1})
        self.assertEqual(result["qa_rounds"], 2)
        self.assertEqual(result["worktrees"], str(self.workspace / "shop.worktrees"))

    def test_nearest_file_wins_key_by_key(self):
        self.write(self.home / ".config/opencode/swarm.json", {"max": {"dev": 2, "eval": 0}})
        self.write(self.workspace / ".opencode/swarm.json", {"max": {"qa": 1}, "qa_rounds": 3})
        self.write(self.project / ".opencode/swarm.json", {"max": {"dev": 4}})
        result = self.limits()
        self.assertEqual(result["max"], {"design": 1, "dev": 4, "qa": 1, "eval": 0})
        self.assertEqual(result["qa_rounds"], 3)
        self.assertEqual([pathlib.Path(s).name for s in result["sources"]],
                         ["swarm.defaults.json", "swarm.json", "swarm.json", "swarm.json"])

    def test_unknown_roles_are_reported_not_used(self):
        self.write(self.project / ".opencode/swarm.json", {"max": {"designer": 2}})
        result = self.limits()
        self.assertEqual(result["max"]["design"], 1)
        self.assertEqual(result["unknown_roles"], ["designer"])

    def test_invalid_values_fail(self):
        self.write(self.project / ".opencode/swarm.json", {"max": {"dev": -1, "qa": "two"}, "qa_rounds": 0})
        run = self.limits(check=False)
        self.assertEqual(run.returncode, 1)
        for text in ("max.dev must be", "max.qa must be", "qa_rounds must be"):
            self.assertIn(text, run.stderr)

    def test_worktrees_folder_can_move(self):
        self.write(self.project / ".opencode/swarm.json", {"worktrees": ".trees"})
        self.assertEqual(self.limits()["worktrees"], str(self.project / ".trees"))


if __name__ == "__main__":
    unittest.main()
