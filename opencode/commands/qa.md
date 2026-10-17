---
description: QA review of a change (uncommitted, branch, PR or path) against the task, docs, specs, tests and conventions
agent: qa
subagent: true
---
Run a QA review.

Target, task and app URL as given (any of them may be missing):

$ARGUMENTS

If no target is given, review the uncommitted changes and the current branch against its base. If no task is given, take it from the PR and the commit messages, and report as missing information whatever they don't say.

Follow your method in order. Its skills are part of it, so load them with the skill tool: `qa-naming-and-values` and `qa-test-audit` always, `qa-api-contract` when there is an API spec, and `qa-browser` when there is a page to check.

Repository state when the command ran:

!`git status --short --branch 2>&1 | head -40`
