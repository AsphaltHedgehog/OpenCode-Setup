---
name: Swarm
description: The sprint swarm's limits and how they are set. Covers the maximum number of design, dev, qa and eval agents a sprint may run at once, the qa fix rounds and the worktree folder. Defaults come from the harness and are overridden per machine, workspace or project in .opencode/swarm.json. Use it before running a sprint, or to explain or change the limits.
---

# Swarm limits

The numbers are **upper limits, not quotas**. The lead starts only as many agents as the work needs and never more than a role's limit. A sprint of one small task uses one dev and one reviewer, even when the limits allow three and two. A role whose limit is `0` is skipped.

## Settings

```json
{
  "max": { "design": 1, "dev": 3, "qa": 2, "eval": 1 },
  "qa_rounds": 2,
  "worktrees": "../{repo}.worktrees"
}
```

| Key | Meaning |
|---|---|
| `max.design` | design agents writing spec items at the same time |
| `max.dev` | dev agents building at the same time, each in its own worktree |
| `max.qa` | qa reviewers on one change. The lead uses one, and more only for risky changes: contracts, data, security, large diffs |
| `max.eval` | `1` closes the sprint with an evaluation; `0` skips it |
| `qa_rounds` | review-and-fix rounds per change before the lead stops and asks you |
| `worktrees` | where task worktrees go, relative to the repository root; `{repo}` is the repository's folder name |

## Where they come from

From lowest to highest precedence. A later file replaces only the keys it sets:
1. `swarm.defaults.json` in this skill's folder, the harness defaults;
2. this machine: `~/.config/opencode/swarm.json`;
3. each `.opencode/swarm.json` from the home folder down to the project; the nearest wins. This is how a workspace and then a project override the harness.

To see the result for a project:

```bash
python3 <this skill's folder>/scripts/swarm_limits.py <project>
```

It prints the merged limits, the absolute worktree folder, and the files it read, in order. It exits with an error if a value is invalid, for example a negative count. Roles it doesn't know are listed and ignored.
