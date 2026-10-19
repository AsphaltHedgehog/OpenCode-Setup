---
name: QA naming and values
description: Checklist for reviewing a change at the level of abstraction (names, signatures, constants, defaults, units, enums and messages) against the vocabulary of the project's docs and specs. Use it when reviewing added or changed public functions, routes, config keys, constants or user-facing text.
---

# Names and values

Review what a caller, a reader or a user meets, not how it is built. Start from a list of the added or changed public elements:
- exports;
- routes and CLI flags;
- config keys and environment variables;
- database columns and events;
- error codes and constants;
- user-facing strings.

## Names

For each element, write one line in this shape: `name: what the name promises / what the docs or spec call it / what it does`. Take "what it does" from the signature, the tests and the docstring. Every place where the three disagree is a finding.

- Verbs match effects. `get`, `find`, `is`, `has`, `check`, `validate` and `compute` don't write, send, cache or mutate. `save`, `send` and `delete` do what they say and nothing more.
- Booleans read as yes/no questions (`isActive`, `hasAccess`) and are named for the true case, with no double negatives such as `disableX = false`.
- Collections are plural, counts say `count`, and ids say `id`. Where the language doesn't show it, optional values say they are optional.
- When the type doesn't carry the unit or format, the name does: `timeoutMs`, `sizeBytes`, `priceCents`, `createdAtUtc`, `ratePct`.
- One concept has one name. The code uses the term from the spec or docs (customer, client or account, not a mix). Flag synonyms that the change introduces, and any name reused for a second concept.
- Names follow the conventions of the neighbouring code: casing, prefixes, file names and error class names. Check two or three sibling modules before calling something inconsistent.
- Watch for names that became wrong with this change: a function that grew a side effect, a variable whose meaning changed under the same name, or a test whose name no longer matches its assertion.

## Signatures

- Parameter names and order match similar functions in the project, and the same thing sits in the same position.
- Required versus optional matches the spec: required fields in OpenAPI, nullable columns.
- Each signature makes clear which result means "not found" and which means "error": null, empty or an exception. Unknown must never look like empty.
- Sync versus async, pagination and sort order are stated wherever callers depend on them.

## Values

Every literal and default that the change adds or changes needs a source: the spec, a doc, the task, a config file or a constants module. A value with no source is a finding (a magic value) or a question for the author.

- **Limits and boundaries:** inclusive versus exclusive (`<=` or `<`), off-by-one at the edges, maximum lengths, page sizes, retry counts and timeouts. Check that the tests cover the boundary itself.
- **Units and scales:** milliseconds or seconds, bytes or kilobytes, cents or whole currency units, percentages as 0–1 or 0–100.
- **Time:** stored in UTC and converted for display. Date-only values need a time zone and DST rule, and end dates must say whether they are inclusive.
- **Money and numbers:** rounding mode, precision and currency. Money is never a binary float.
- **Enums and statuses:** complete compared with the spec, with spelling matching exactly. The unknown or default branch is handled, and stored values are never renumbered or reused.
- **Defaults:** safe when unset, and identical in the code, the config, the docs and the spec.
- **Patterns and formats:** regexes are anchored and match the documented format, and the examples in the docs pass them.
- **Feature flags and config keys:** name, default and docs agree, and removing a key is handled.

## Messages and text

- An error message says what happened and what to do next. It doesn't show end users secrets, stack traces or internal ids.
- Error codes and HTTP status codes match the spec and are consistent with similar errors in the project.
- UI text matches the wording in the spec or design. Empty, loading, error and unknown states are each distinct and worded.
- Log and event names follow the project's scheme and carry no secrets or personal data.

Report each problem as a finding that names the element, the expected name or value with its source, and what the code has.
