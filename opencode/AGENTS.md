# Harness rules for every session

These rules come from the halfling-harness global layer, and they apply in every project. A project's own AGENTS.md adds to them, and it wins where the two disagree.

## Document conflicts go to the design agent

When two documents disagree, don't resolve the conflict in this session. That covers:
- two spec items;
- a spec item and the API contract it names (OpenAPI, AsyncAPI, protobuf, GraphQL);
- the README or `docs/` and a spec item or a contract;
- an ADR and a later decision;
- merge conflicts inside any of these files.

Launch the `design` subagent with both sides, their locations, and what you were doing when you found the conflict. Design applies the rule that settles it, or turns it into a decision when no rule does.
- **Its questions:** when it returns open questions, ask the user each one in turn, with design's recommended answer first, and resume the same design session with the answers.
- **Afterwards:** carry on with your own task once design reports that the documents agree.

Code that disagrees with a document is not a document conflict. The dev agent fixes the code, or design changes the document through a decision.
