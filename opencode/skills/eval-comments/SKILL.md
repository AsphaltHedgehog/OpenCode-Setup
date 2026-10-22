---
name: Eval comments
description: Checklist for judging the comments a range of commits added or changed. It finds comments that restate the code, narrate history, talk to a reader or an AI, repeat a signature, contradict the code, or comment out code, and measures them against the project's own comment density. Use it at the end of a sprint, or when a review says comments are too wordy.
---

# Comments review of a range

A good comment says **why**: a constraint, a workaround and its link, a non-obvious invariant, a unit, or a lesson learned the hard way. Everything the code already says is noise, and noise hides the comments that matter.

## First, the project's norm

- Measure comment density per language as comment lines divided by code lines, using `cloc` or `scc` if installed, or `rg -c` for comment markers and `wc -l`. Do it for the whole repository and for the files the range touched.
- A file whose density jumped during the range is where to look first. Judge against this project's norm, never a fixed number: some codebases document heavily on purpose, and AGENTS.md or a style guide may say so.

## What to look for

Read the comment lines the range added or changed (`git diff <base>..HEAD`):

1. **Restates the code.** `// increment the counter`, `# return the result`, `/* loop over users */`.
2. **Narrates history.** "changed to", "now uses", "previously", "new:", "updated", "fixed bug where". The history belongs in the commit message.
3. **Talks to a reader.** "This function is responsible for", "Note that", "It's important to", "As you can see", "Here we", decorative banners over a few lines, emoji. These read as written for a reviewer or by an assistant, not for the next maintainer.
4. **Repeats the signature.** Docstrings that restate parameter names and types (`x: the x`) on small or private functions. Keep docstrings where the project's public API style requires them.
5. **Contradicts the code.** The comment claims a behaviour, unit, order or limit that the code no longer has. This is the costliest kind; check each comment near changed logic.
6. **Commented-out code.** It is version control's job.
7. **Too long for its point.** A paragraph where one line would do. Propose the one line.

## Recommending a decision

- Group the findings by file, or by kind when they repeat, so that a whole group becomes one question: "trim these 9 comments in cart.js".
- For each comment give the change you propose:
  - **delete** it;
  - **shorten** it, quoting the shorter text that keeps the why;
  - **move** it to the commit message or an ADR.
- Contradicting comments are their own question, because they can mean the code is wrong rather than the comment.
- Never flag a comment that carries a why, even a long one, unless it contradicts the code.
