# halfling-harness

A harness for [opencode](https://opencode.ai) v2: MCP servers, an outside-in QA agent, skills and slash commands. It has two layers:

- **The global layer, `opencode/`.** It is public, applies to every project, and is what this repo is about.
- **The private layer, `private/`.** It holds your own rules and config for one workspace folder, for example the repositories of one company. Git ignores it, so it is never pushed.

A project's own `.opencode/` folder is applied after both layers, so project rules still win where they disagree.

It uses only v2 configuration: `mcp.servers`, ordered `permissions` lists, and the `agents/`, `commands/` and `skills/` folders. It was built and tested on opencode 2.0.25 on macOS. The v2 documentation is at [opencode.ai/v2/docs](https://opencode.ai/v2/docs/).

## Install

You need:
- opencode v2;
- Node.js 20 or later, because `npx` runs chrome-devtools-mcp;
- Google Chrome;
- Python 3, for the check script.

```bash
git clone https://github.com/AsphaltHedgehog/halfling-harness.git
cd halfling-harness
./install.sh --dry-run      # show what would be linked
./install.sh                # link the global layer into ~/.config/opencode
python3 scripts/check.py    # ask opencode what it loaded
```

`install.sh` only creates symlinks, and it never replaces a file that isn't one of its own links. Your own `~/.config/opencode/opencode.json` stays in place, because opencode reads both `opencode.json` and `opencode.jsonc` from the same folder and merges them. To remove everything again, run `./install.sh --uninstall`.

### The private layer

Put your own rules in `private/`, using the layout of an opencode config folder:
- `private/AGENTS.md` holds the instructions;
- `private/opencode/` holds `opencode.json`, plus `agents/`, `commands/` and `skills/` if you need them.

Then link the layer into the folder that holds the repositories it is for:

```bash
./install.sh --private-to ~/work/acme    # links ~/work/acme/.opencode and ~/work/acme/AGENTS.md
```

opencode reads `.opencode/` and `AGENTS.md` from every folder above the one it starts in, so every project under that folder gets the private layer on top of the global one. The TUI, the desktop app and IDEs all pick it up. `install.sh` remembers the folder in `private/.workspace`, so a plain `./install.sh` re-links both layers afterwards. `scripts/check.py` fails if anything in `private/` is ever tracked by git.

### Open opencode

```bash
launch/oc.command                  # opencode here; outside the private workspace, pick a project from it
launch/oc.command <folder> [args]  # opencode in <folder>; further arguments go to opencode
```

The launcher names no projects. It finds every git repository or worktree directly in the private workspace and offers them as choices, which is also what happens when you double-click it in Finder. If the links are missing, it runs `install.sh` first.

## What's inside

| Path | What it is |
|---|---|
| `opencode/opencode.jsonc` | The MCP servers, plus the one global permission rule |
| `opencode/agents/qa.md` | The QA agent |
| `opencode/agents/dev.md` | The developer agent |
| `opencode/agents/eval.md` | The evaluation agent for the end of a sprint |
| `opencode/agents/deps.md` | The dependency scout |
| `opencode/agents/design.md` | The software designer and keeper of the specs |
| `opencode/commands/qa.md`, `qa-ready.md` | The `/qa` and `/qa-ready` commands |
| `opencode/commands/dev.md` | The `/dev` command |
| `opencode/commands/eval.md` | The `/eval` command |
| `opencode/commands/deps.md` | The `/deps` command |
| `opencode/commands/design.md` | The `/design` command |
| `opencode/skills/qa-*/SKILL.md` | Checklists that the QA agent loads when a step needs them |
| `opencode/skills/eval-*/SKILL.md` | The evaluation agent's architecture and comments checklists |
| `opencode/skills/specs/` | The spec item format, and the trace script that links specs to code by ID |
| `private/` | Your own layer for one workspace. Git ignores it, so it never reaches GitHub |
| `install.sh` | Links the global layer into `~/.config/opencode` and `private/` into its workspace |
| `launch/oc.command` | Opens opencode in a project with the harness |
| `scripts/check.py` | Checks the setup with opencode's own loader |
| `docs/ideas.md` | Where the harness can go next |

### MCP servers

| Server | What it's for | Notes |
|---|---|---|
| `chrome-devtools` | Lets QA drive a real Chrome: accessibility snapshots, console, network, screenshots, Lighthouse | Pinned to [chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp) 1.10.1. Runs headless with a throwaway profile. Usage statistics and CrUX lookups are off, so page URLs aren't sent to Google, and auth headers are redacted. Only the `qa` agent sees its tools. |
| `context7` | Up-to-date documentation for libraries and frameworks | A remote server. It works without a key, and a key raises the rate limit (see the comment in the config). |

Two well-known servers are left out on purpose:
- **GitHub MCP:** the `gh` CLI covers the same ground with far fewer tokens.
- **Playwright MCP:** it overlaps with Chrome DevTools.

## The QA agent

QA reviews a change from the outside in.
- **Contract before code:** it first collects what was asked and what is written down (the task, docs, OpenAPI and other specs, tests, and the conventions of the code around the change), and only then reads the change.
- **Surface first:** it judges names, signatures, values and messages the way a caller or a user meets them, and opens function bodies only to check a specific suspicion.
- **Missing information is a finding:** it runs with a fresh context, so anything not written down becomes a question to the author rather than a guess.
- **Evidence:** it runs the tests and, when there is a page, checks it in Chrome. Before reporting, it tries to refute each of its own findings.

The prompt itself is the source of truth: [`opencode/agents/qa.md`](opencode/agents/qa.md).

### Use it

| You type | What QA reviews |
|---|---|
| `/qa` | The uncommitted changes and the current branch against its base |
| `/qa 123` | Pull request #123 (needs `gh`) |
| `/qa feature/login Users can reset their password by email` | A branch, checked against the task you give |
| `/qa http://localhost:3000/orders` | The same as `/qa`, plus the running page in Chrome |
| `/qa-ready <task text or issue URL>` | Nothing yet: it checks that the task says enough to build and test it, before anyone writes code |

You can also press Tab to switch to `qa` and talk to it directly, or ask `build` to "use the qa subagent to review my changes".

Every report has the same parts:
- a verdict: PASS, PASS WITH NOTES, FAIL or BLOCKED;
- a requirements table that traces each requirement to its source, its implementation and its test;
- findings ordered by severity, each with its location, the expected and observed behaviour, and the evidence;
- missing information, written as questions for the author;
- what it could not verify;
- the commands it ran.

### What it may do

- **Edits:** QA is read-only, so file edits are denied.
- **Without asking:** git inspection, `gh pr view` and `gh pr diff`, read-only helpers, and common test runners (npm, pnpm, yarn, bun, vitest, jest, pytest, unittest, go, cargo, dotnet, maven, gradle and make).
- **Never:** commit, push, reset, checkout, merge, `rm`, `--fix`, `sed -i` or redirecting output into files.
- **Asks first:** any other shell command. In a non-interactive `opencode run`, a command that needs approval is rejected rather than asked.

Agent rules are applied after every config file's top-level rules. As a result, QA asks before running a test command that your project allows only at the top level. To let QA run a project's own command, add it for `qa` in the project's config:

```jsonc
// <project>/.opencode/opencode.jsonc
{
  "agents": {
    "qa": {
      "permissions": [
        { "action": "shell", "resource": "./scripts/verify.sh *", "effect": "allow" }
      ]
    }
  }
}
```

### Model

QA uses the model of the session it runs in. You can pin a different one by adding `model: provider/model` to the frontmatter of `agents/qa.md`. A model family other than the one that wrote the code tends to catch different mistakes.

## The dev agent

Dev turns a task into a small, tested, reviewed change.
- **Contract first:** it collects the same written sources QA uses before it edits anything. For anything bigger than a small fix, it runs `qa` in ready mode first.
- **Decisions are yours:** it looks facts up itself and asks you only for decisions, one question at a time, each with its recommended answer.
- **Test first:** a bug becomes a failing test before it gets a fix, with expected values from the spec rather than from the code.
- **Reviewed before commit:** it reads its own diff against the `qa-naming-and-values` checklist, then has the `qa` agent review the change and fixes what QA confirms.
- **Small commits:** it commits on a topic branch in logical commits, using the project's message style.

Run it with `/dev <task>`, or press Tab to switch to `dev`. The prompt is the source of truth: [`opencode/agents/dev.md`](opencode/agents/dev.md).

### What it may do

- **Without asking:** edit files, inspect git, create a topic branch, stage and commit, and run tests, linters, formatters, type checks and builds.
- **Asks first:** pushing, installing packages, `npm run` scripts other than test, lint, typecheck, build and format, and any other shell command.
- **Never:** force-push, push to `main` or `master`, `git reset --hard`, `git clean`, discard changes with `git checkout --`, merge a PR, publish a release or run a workflow.
- **Subagents:** `qa`, `explore` and `general`.

As with QA, a project can allow its own commands for `dev` under `agents.dev.permissions` in its config.

## The design agent and spec items

Design turns a task into a **spec item** before code is written, and keeps every item true to the code afterwards.

Every implemented task is saved in the repository as one markdown file. The file is named `docs/specs/<task-slug>-<ID>.md`, and its first line is `# <ID> <title>`, for example `# SPEC-12 Orders: limit parameter`. Each item has a state (`draft`, `approved`, `implemented`, `deprecated`), numbered acceptance criteria (`AC-1`, `AC-2`) and its decisions. It is found **by ID, never by path**, in the spirit of Google's AIPs. IDs are never reused.
- **design** writes the item and asks you each open decision one question at a time, with its recommended answer. It updates the API contract first, writes an ADR for each structural choice, and hands dev a plan in small steps. It may write only specs, ADRs and contract files.
- **dev** reads the item by ID, tags the code with `spec: SPEC-12` and each test with `spec: SPEC-12/AC-2`, and marks the item implemented. If a task had no item, dev writes one, so every implemented task is saved.
- **qa** takes its requirements from the item's acceptance criteria.
- **eval** treats what the trace reports as findings, and never counts `spec:` tags as wordy comments.

The trace is a script that ships inside the `specs` skill:

```bash
python3 opencode/skills/specs/scripts/spec_trace.py <repo> [--strict] [--json]
```

It reports:
- broken or duplicate IDs;
- approved items no code implements, and implemented criteria no test proves;
- tags pointing at unknown or deprecated items;
- items changed after their code.

`--strict` makes it usable in CI. `scripts/check.py` runs its tests.

Run design with `/design <task>`. When it runs as a subagent it can't ask you anything, so it returns its open questions with recommendations and keeps the item as a draft.

## The eval agent

Eval closes a sprint or a feature set. It finds what the sprint left behind, then grills you about it, in the spirit of Matt Pocock's [grilling skill](https://github.com/mattpocock/skills).
- **Range:** everything since the last evaluation, using the commit recorded in `docs/evaluations/`. The first time, it starts from the newest tag. You can also give it a range: `/eval v1.4.0..HEAD`.
- **What it looks for:**
  - **unresolved work:** TODO markers, skipped tests, leftover debug code, unanswered review threads, issues still open, and docs that didn't follow a change;
  - **architecture:** dependency direction and cycles, one rule implemented twice, growth hot spots, abstractions with one user, leaky boundaries, failures that disappear, and drift from the README, ADRs or AGENTS.md;
  - **comments:** comments that restate the code, narrate history, talk to the reader or contradict the code, judged against the project's own comment density.
- **Grilling:** it asks you one question at a time, each with its recommended answer: fix now, ticket, accept with a reason, or write an ADR. It looks facts up itself and asks you only for decisions.
- **The record:** it writes `docs/evaluations/<date>.md` as it goes, and that is the only file it may change. The record ends with a ready-to-run `/dev` task for the fix-now items, and the agent leaves it uncommitted for you to review.

Run it with `/eval` as the main agent of a session, because a subagent can't hold an interview. In a non-interactive run it writes its proposed decisions and stops. It doesn't judge how up to date your dependencies are; it only notes the ones the sprint added.

## The deps agent

Deps finds which dependencies should move, how risky each move is, and what in your code each move would touch. It changes nothing. Its upgrade batches are written as `/dev` tasks.
- **Inventory:** package manifests and lockfiles, toolchain pins, Docker base images, GitHub Actions versions and pinned `npx` packages.
- **Outdated and vulnerable:** each ecosystem's own read-only commands (`npm outdated`, `npm audit`, `pip3 index versions`, `go list -m -u`, `cargo audit`, `osv-scanner` and so on), when they are installed. It never installs a tool; a missing one goes under "Not checked".
- **Cooldown:** a release younger than 14 days is held back unless it fixes a vulnerability that affects you. Fresh releases are where supply-chain attacks and quick reverts land. A project can set a different cooldown in its AGENTS.md.
- **Risk:** for every major update and every security fix, it reads the changelog and finds the call sites in your code that the breaking changes touch.
- **Batches:** security now, a safe patch-and-minor batch, one batch per major, and a hold list, each with a ready-made `/dev` task.

Run `/deps` (or `/deps npm`, `/deps app/`) as a background subagent. It runs on its own schedule, for example weekly or before a release, so it is separate from the end-of-sprint evaluation.

## Check it

`python3 scripts/check.py` links `opencode/` into a throwaway project and asks opencode what it loaded. It verifies that:
- every agent, command and skill is loaded;
- agent frontmatter uses only v2 keys;
- the QA permission rules produce the outcomes worked out by hand;
- every MCP package is pinned and every server connects.

Afterwards it disconnects the servers it started. Run it after every change, and after upgrading opencode.

Each check project is `~/.cache/halfling-harness/check/<layer>-<hash of its files>`, so every version of the files gets a fresh folder. When `private/` exists, the script also checks that git ignores it and tracks none of its files, that the workspace links point at it, and that its config loads. These folders are kept on purpose: deleting a folder opencode has loaded breaks `opencode reload` (see below). Each one holds only a symlink.

## v2 gotchas found while building this

- **A single v1 key disables the agent's permissions.** If an agent's frontmatter contains any v1 key (`temperature`, `tools`, `permission`, `prompt`, `maxSteps` and so on), opencode reads the whole file as a v1 agent, and the v2 `permissions` list is silently dropped. A read-only agent then becomes able to edit files and push. `scripts/check.py` fails on this.
- **Edits through a symlink are missed.** The background service keeps a folder's agents, commands and skills from the first time it loads that folder, and it doesn't notice edits made through a symlinked `.opencode` (which is how `install.sh` links this repo). After you change or pull this repo, run `opencode reload`. Be aware that it rebuilds every loaded folder and cancels any pending permission prompts.
- **Deleted folders break the reload.** If you delete a folder opencode has loaded, `opencode reload` fails with `DirectoryNotFoundError` until the service restarts (`opencode service restart`).
- **Agents load a moment late.** In a folder opencode hasn't seen before, the agents arrive a moment after the first request, so `opencode debug agents` can miss them. Ask again.
- **Piped output can be cut short.** `opencode api` can truncate a large answer when its output goes into a pipe. Write it to a file.
- **`mcp.disconnect` fails in 2.0.25.** The `opencode api mcp.disconnect` operation errors, while `opencode api POST /api/experimental/mcp/<server>/disconnect` works.
- **MCP tool permissions:** an MCP tool's permission action is `<server>_<tool>`, so this setup uses `chrome-devtools_*`.
- **Config path variables are ignored.** The v2 background service ignores `OPENCODE_CONFIG` and `OPENCODE_CONFIG_DIR`, which is why the install works with symlinks.

## Prior art

The QA method borrows ideas, not text, from these permissively licensed projects:
- [obra/superpowers](https://github.com/obra/superpowers) (MIT): "a spec's silence is not permission", and treating the implementer's report as unverified claims.
- [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) (MIT):
  - code review: the claims check, the verification gap, and intent alignment, which lists the defensible readings of a task;
  - the test-architecture trace: a requirements-to-tests matrix with a gate.
- [github/spec-kit](https://github.com/github/spec-kit) (MIT): a read-only `/analyze` that builds a requirements inventory before anything else.
- [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official): the `code-review` and `pr-review-toolkit` plugins (Apache-2.0), which separate the review pass from a verification pass.
- [darcyegb/ClaudeCodeAgents](https://github.com/darcyegb/ClaudeCodeAgents) (MIT): the spec-audit agent "Jenny", which classifies findings as Missing, Incomplete, Incorrect or Extra.

Larger agent collections to adapt from:
- [wshobson/agents](https://github.com/wshobson/agents) (MIT, with an opencode exporter);
- [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) (MIT);
- [github/awesome-copilot](https://github.com/github/awesome-copilot) (MIT).

Most of them are written for Claude Code or opencode v1. Before you import one, convert its `tools`, `permission` or `temperature` fields into a v2 `permissions` list, for the reason given in the first gotcha above.

## License

MIT
