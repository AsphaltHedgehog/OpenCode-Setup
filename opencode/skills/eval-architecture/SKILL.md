---
name: Eval architecture
description: Checklist for judging the architecture of a range of commits. It covers dependency direction and cycles, the same rule implemented twice, growth hot spots, abstractions with one user, leaky boundaries, error handling that hides failures, contract changes, configuration sprawl, test coverage of new modules, and drift from documented decisions. Use it at the end of a sprint or before a release.
---

# Architecture review of a range

Judge the code as it stands at the end of the range, and use the range to see which way it moved. Each finding names its evidence (`path:line` or a commit) and the source it goes against:
- the README's architecture section, an ADR or AGENTS.md;
- otherwise, the direction the existing code already follows.

Without a source, a finding is a question, not a verdict.

## First, the map

- List the top-level modules or packages and what each one is for. Take that from the README or docs when they say it; otherwise infer it from the folder names and say that you inferred it.
- Collect the imports the range added: `git diff <base>..HEAD` lines that add `import`, `from … import`, `require(` or `use`. Note which module now depends on which.

## The checklist

1. **Dependency direction.** A new import that runs against the documented layering, or against the direction the rest of the code follows. Examples: the domain importing the web layer, a shared library importing an app, a lower layer reaching up.
2. **Cycles.** Module A now imports B while B already imports A. Check the reverse with `git grep`.
3. **One rule, two places.** The same constant, validation, rounding, formatting or permission rule now lives in two places, such as backend and frontend or two services. Search for the literal values and the names. If the two copies disagree, report both locations, and recommend which one should be the master.
4. **Growth hot spots.** The files with the most added lines (`git diff --stat <base>..HEAD | sort -k3 -n`). A file that took on a second job, or a function far longer than the project's usual length, is a candidate to split. Say which job would move where.
5. **Abstraction with one user.** A new interface, base class, factory, plugin point or configuration option that has exactly one implementation or caller. Recommend inlining it unless a written plan needs the second one.
6. **Leaky boundaries.** I/O (SQL, HTTP, filesystem, clock, randomness) appearing in code that was pure before, or business rules appearing in controllers, views, handlers or scripts.
7. **Failures that disappear.** Broad catch blocks, swallowed errors, and fallback values that make "unknown" look like "empty" or "zero". Retries without limits.
8. **Contract changes.** API, schema, event, CLI or file-format changes without a version, a migration path, or an update to the spec and docs.
9. **Configuration sprawl.** New environment variables, flags or settings, defaults repeated in several places, and options nobody documented.
10. **Untested structure.** A new module or layer with no tests, or production code that grew far more than its tests during the range.
11. **Drift from decisions.** Code that contradicts an ADR, the README's architecture section, AGENTS.md, or a decision recorded in an earlier evaluation.

## Recommending a decision

For each finding, propose one of these:
- **fix now:** small, local, and getting worse while it waits;
- **ticket:** real, but bigger than this sprint;
- **accept:** deliberate, and the trade-off is fine. Give the reason;
- **ADR:** a structural choice that future work will keep running into.

Prefer **ADR** when the finding is about direction rather than a single place.
