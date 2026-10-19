# Where this harness can go next

These ideas are ordered roughly by value for effort. None of them is built yet. Each one names the opencode v2 feature it would use.

## 1. Close the loop between "what was asked" and "what QA checks"

- **An `analyst` agent** (primary). It turns a request into numbered requirements with acceptance criteria, plus open questions, and writes them to `docs/tasks/<slug>.md`. `build` implements against that file and `qa` verifies against the same file, so the requirements table in QA's report traces back to a written source rather than to a chat. `/qa-ready` is the read-only half of this today.
- **A task template** in `opencode/commands/task.md` that asks for the fields QA keeps flagging as missing: units, limits, errors, empty and unknown states, and who the user is.

## 2. More specialised agents

| Agent | Mode | Permissions | Job |
|---|---|---|---|
| `test-author` | subagent | edits only in test folders | Writes the failing test first, from a bug report or an acceptance criterion |
| `docs-keeper` | subagent | edits only `docs/**`, README and spec files | Brings the docs and the OpenAPI spec in line with a change, or reports drift |
| `security-reviewer` | subagent | read-only | Secrets, authorisation, injection, unsafe defaults and dependency changes |
| `qa-verifier` | subagent | read-only | Adversarial second pass that tries to refute each QA finding. It needs `subagent_depth: 2` so that qa can launch it. |

## 3. Gates that don't depend on the model remembering

- **A v2 plugin** that refuses `git commit` and `gh pr create` until a QA verdict of PASS or PASS WITH NOTES exists for the current diff hash. The verdict would be stored in `.qa/<hash>.json`. v1 plugin code doesn't run in v2, so it has to be written against the v2 plugin API.
- **`policies`** for the few hard limits that no project should be able to relax: force-push, `reset --hard`, reading `.env` files and `rm -rf` outside the project. A policy turns allow or ask into deny and wins over project config.

## 4. Review with a different model

Run `qa` on a different model family from the one that wrote the code. It won't share the same blind spots. This takes one frontmatter line (`model: provider/model`). Pick it per machine, because models depend on which providers you're logged in to.

## 5. Distribute without symlinks

Publish `opencode/skills/` as an HTTP skill catalog (an `index.json` on GitHub Pages). A machine then only needs `"skills": ["https://…/skills/"]` in its config, and that works on Windows, where symlinks need Developer Mode or admin rights.

## 6. Better browser evidence

- Restrict QA's Chrome to local and test URLs with `--allowedUrlPattern` (Chrome 149+), so a review can never touch production.
- Record a reproduction video with `--experimentalScreencast` (needs ffmpeg) and attach it to a finding.

## 7. QA memory

Let `qa` write its reports to `.qa/`, allowing edits there and nowhere else. A later review could then check whether old findings came back, and a lead could see what keeps going wrong.

## 8. QA in CI

Run `opencode run --agent qa --format json` on every pull request in CI and post the report as a PR comment. A person still merges.

## 9. Version the private layer

`private/` is ignored by this repo's git, so today nothing versions it. It can become a git repository of its own, inside the same folder, pushed to a private remote. The outer repo keeps ignoring it, so the folder layout stays the same and the rules get history, review and a backup. `scripts/check.py` would then also check that the private repository has a remote and no unpushed work.
