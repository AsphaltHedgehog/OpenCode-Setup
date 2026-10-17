---
name: QA test audit
description: Checks that the tests prove the requirements. Covers tracing each requirement to a test, the quality of assertions, edge and negative cases, test hygiene, and whether a run actually collected any tests. Use it when a change adds or modifies tests, or when you have to judge whether a change is tested.
---

# Test audit

## Trace requirements to tests

Build a table with one row per requirement: the requirement, the test names that cover it, and what each test asserts.
- A requirement that no test asserts is untested, however high the coverage number is.
- A test that maps to no requirement may only be testing implementation detail. Mention it only if a harmless refactor would break it.

## Assertion quality

- Expected values are worked out independently: from the spec, by hand, or from a known-good case. They are never copied from the code's current output, and never computed with the function under test.
- Assertions check values, not mere presence: `== 42`, not `is not None`. An error test checks the exact error or code, not just that something was raised.
- Snapshot tests are reviewed and small enough to read. A snapshot that changes in the diff is a behaviour change and needs a reason.
- A test must not merely check that a mock returned what it was told to return. Mocked contracts (HTTP, database) must match the real spec, so compare mocked payloads with the OpenAPI or schema.

## Coverage of behaviour

- **Boundaries:** test at each limit, just below it and just above it.
- **Negative paths:** invalid input, missing fields, unauthorised, not found, conflict, timeout, and the empty and unknown states.
- **Bug fixes:** a regression test exercises the exact condition from the bug report and would fail without the fix. Check this by reading the test.
- **Time, locale and concurrency:** when the change touches them, tests use a fixed clock and an explicit time zone, cover the DST edge, and don't depend on ordering.

## Test hygiene

- Look for newly skipped or focused tests: `.skip`, `xit`, `it.only`, `fdescribe`, `@pytest.mark.skip`, `t.Skip()`.
- Look for flaky patterns: sleeps, real network calls, the real clock, unseeded randomness, order dependence and shared state.
- When a test was changed to match new behaviour, ask whether the old expectation was wrong or whether a requirement changed without anyone saying so.

## Running

- Run the narrowest command that covers the change first, then the whole suite if it is cheap. Record the exact command and its summary line.
- "0 tests collected", "no tests found", or a runner that exits before collecting counts as a failure, never as a pass.
- If the tests need something you don't have (a database, the network, secrets), say what it is and list it under "Not verified". Never fake the environment.
