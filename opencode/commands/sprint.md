---
description: Run a sprint as a team (design, parallel devs in worktrees, qa, eval) within the swarm limits
agent: lead
subagent: false
---
Run this sprint:

$ARGUMENTS

Follow your method in order. Load the `swarm` skill first, then the `specs` skill.

Repository state when the command ran:

!`git status --short --branch 2>&1 | head -20`

Spec items in this repository:

!`ls -1 docs/specs 2>/dev/null | tail -30`
