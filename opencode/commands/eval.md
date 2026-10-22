---
description: End-of-sprint evaluation - find unresolved issues, architecture mistakes and wordy comments, then decide each one with you
agent: eval
subagent: false
---
Evaluate the sprint.

Range or starting point, if given (otherwise use the last evaluation, then the newest tag):

$ARGUMENTS

Follow your method in order. Its skills are part of it: load `eval-architecture` and `eval-comments` with the skill tool before those sweeps.

Earlier evaluations in this repository:

!`ls -1 docs/evaluations 2>/dev/null | tail -5`

Newest tag:

!`git describe --tags --abbrev=0 2>&1 | head -1`
