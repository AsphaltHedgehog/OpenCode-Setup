---
name: Specs
description: The format and rules for spec items in docs/specs/. Each item is one markdown file per task, named <task-slug>-<ID>.md, with the first line "# <ID> <title>". The skill also covers the "spec: <ID>" tags in code and tests and the trace script that links specs to code and tests by ID. Use it whenever you write, implement, review or audit a spec item.
---

# Spec items

Every task that gets implemented is saved as a spec item in the repository, in `docs/specs/`. An item is found by its **ID**, never by its path: renaming or moving a file breaks nothing, because code, tests, reviews and evaluations all cite the ID.

## Files and IDs

- Use one file per task: `docs/specs/<task-slug>-<ID>.md`, for example `docs/specs/orders-limit-parameter-SPEC-12.md`.
- The first line is `# <ID> <title>`, for example `# SPEC-12 Orders: limit parameter`. The ID in that line is the source of truth, and the file name must end with the same ID.
- An ID is `<PREFIX>-<number>`.
  - **Prefix:** `docs/specs/README.md` can name the project's prefix on a line `Prefix: ORD`. Without it, the prefix is `SPEC`.
  - **Number:** a new item takes the highest existing number for that prefix plus one, counting deprecated items too.
  - **Never reuse an ID.** A replaced item keeps its ID with `State: deprecated` and names its successor.

## Template

```markdown
# SPEC-12 Orders: limit parameter

State: draft
Created: 2026-10-22 · Updated: 2026-10-22
Links: depends on SPEC-3 · ADR-0007 · replaces SPEC-9

## Why
One paragraph: the problem, and who has it.

## Behaviour
What the system does, in the user's or caller's terms. Units, defaults, limits, errors, and the empty and unknown states.

## Contract
The API operation, schema, event or CLI this touches, cited by name, for example `openapi.yaml#/paths/~1orders/get`. The contract file stays the source for the contract itself; don't copy it here.

## Acceptance criteria
- AC-1 Without `limit`, the newest 20 orders come back.
- AC-2 `limit=101` returns 400 with code `invalid_limit`.

## Decisions
- 2026-10-22 An empty `?limit=` is invalid (400), not the default. Asked and answered in design.

## Plan
1. Parse and validate `limit` (AC-2). 2. Apply it to the query (AC-1). 3. Document it in the README.

## Out of scope
- Cursor pagination (SPEC-14).
```

## States

| State | Meaning | Who sets it |
|---|---|---|
| `draft` | Being designed; open decisions remain | design |
| `approved` | Decisions settled; ready to build | design, after the user confirms |
| `implemented` | Code and tests carry its tags | dev, when it commits the work |
| `deprecated` | Replaced or dropped; keeps its ID forever | design |

## Tags in code and tests

- Put `spec: SPEC-12` in a comment where the behaviour mainly lives: the handler, the rule or the module. That one place is enough.
- On each test, put `spec: SPEC-12/AC-2`, naming the criterion it proves, in a comment or the test's name.
- A tag is one short line with nothing else in it. It is a link, not a comment, so a comments review never counts it as noise.

## The trace

Run the script that ships with this skill, from the repository root:

```bash
python3 <this skill's folder>/scripts/spec_trace.py .             # report
python3 <this skill's folder>/scripts/spec_trace.py . --strict    # exit 1 on problems (CI)
python3 <this skill's folder>/scripts/spec_trace.py . --json      # for scripts and agents
```

It lists each item with its state, its code tags and its tested criteria, and reports problems:
- a first line without an ID, a file name that doesn't end in the ID, a duplicate ID, or a missing `State:` line;
- an `approved` or `implemented` item that no code carries;
- an `implemented` item whose criteria have no test tags;
- a `draft` item that code already implements;
- tags that point to unknown or deprecated IDs, or to criteria the item doesn't have;
- an item committed after its code, which means the code may no longer match it.
