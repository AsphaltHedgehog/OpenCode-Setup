# Where this harness can go next

These ideas are ordered roughly by value for effort, and none of them is built yet. Each one names the opencode v2 feature it would use. The analyst idea that used to head this list is now the design agent and its spec items.

## 1. Spec items in CI

Run `spec_trace.py --strict` in each project's CI, so a pull request can't merge with an approved item that no code implements, or with criteria that no test proves. Report the trace in the PR as a comment.

## 2. Unattended sprints

A permission prompt in a background session waits until someone answers it. In the test sprints, reviewers and eval still reached for ad-hoc `python3 -c` probes even though the lead told them not to. Each of those stalled its session until the prompt was answered. A small v2 plugin can fix this with the permission hook:
- when no client is attached, or after a few minutes without an answer, it rejects the prompt with a message such as "unattended: note it under Not verified";
- it logs what it rejected, so the morning report shows what each agent wanted to run.

## 3. More specialised agents

| Agent | Mode | Permissions | Job |
|---|---|---|---|
| `test-author` | subagent | edits only in test folders | Writes the failing test first, from a bug report or an acceptance criterion |
| `docs-keeper` | subagent | edits only `docs/**`, README and spec files | Brings the docs and the OpenAPI spec in line with a change, or reports drift |
| `security-reviewer` | subagent | read-only | Secrets, authorisation, injection, unsafe defaults and dependency changes |
| `qa-verifier` | subagent | read-only | Adversarial second pass that tries to refute each QA finding. It needs `subagent_depth: 2` so that qa can launch it. |

## 4. Gates that don't depend on the model remembering

- **A v2 plugin** that refuses `git commit` and `gh pr create` until a QA verdict of PASS or PASS WITH NOTES exists for the current diff hash. The verdict would be stored in `.qa/<hash>.json`. v1 plugin code doesn't run in v2, so it has to be written against the v2 plugin API.
- **`policies`** for the few hard limits that no project should be able to relax: force-push, `reset --hard`, reading `.env` files and `rm -rf` outside the project. A policy turns allow or ask into deny and wins over project config.

## 5. Review with a different model

Run `qa` on a different model family from the one that wrote the code. It won't share the same blind spots. This takes one frontmatter line (`model: provider/model`). Pick it per machine, because models depend on which providers you're logged in to.

## 6. Distribute without symlinks

Publish `opencode/skills/` as an HTTP skill catalog (an `index.json` on GitHub Pages). A machine then only needs `"skills": ["https://…/skills/"]` in its config, and that works on Windows, where symlinks need Developer Mode or admin rights.

## 7. Better browser evidence

- Restrict QA's Chrome to local and test URLs with `--allowedUrlPattern` (Chrome 149+), so a review can never touch production.
- Record a reproduction video with `--experimentalScreencast` (needs ffmpeg) and attach it to a finding.

## 8. QA memory

Let `qa` write its reports to `.qa/`, allowing edits there and nowhere else. A later review could then check whether old findings came back, and a lead could see what keeps going wrong.

## 9. QA in CI

Run `opencode run --agent qa --format json` on every pull request in CI and post the report as a PR comment. A person still merges.

## 10. Version the private layer

`private/` is ignored by this repo's git, so today nothing versions it. It can become a git repository of its own, inside the same folder, pushed to a private remote. The outer repo keeps ignoring it, so the folder layout stays the same and the rules get history, review and a backup. `scripts/check.py` would then also check that the private repository has a remote and no unpushed work.
