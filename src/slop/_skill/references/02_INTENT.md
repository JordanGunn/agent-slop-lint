---
description: When to invoke slop and in what mode.
index:
  - Passive mode
  - Active mode
  - Signals
---

# Intent

## Passive mode

Run slop silently after making code changes. The user did not ask for a
quality check — the agent is self-auditing.

**When:** After completing a multi-file change, refactor, or feature
implementation. Not after trivial edits (typo fix, single-line change).

**Reporting rule:** If clean, say nothing. If violations exist, surface as
a brief aside — violation count and top 1-2 findings. Offer to address
them. Do not interrupt the user's flow.

## Active mode

Run slop because the user asked for a quality check.

**When:** The user says "check quality", "run the linter", "is this
clean", "are there any issues", or similar.

**Reporting rule:** Report the summary — violations per category, top
offenders per category (max 3). Synthesize the interpretation fields. If
the user asks to drill in, run `slop check <category>` for detail.

## Signals

Run slop (passive) when:
- You just completed a PR-sized change
- You refactored a complex area
- You added significant new code across multiple files
- You touched files that appeared in a previous slop report

Run slop (active) when:
- The user asks about code quality, complexity, coupling, or hotspots
- The user asks "did I introduce any problems?"
- The user asks for a pre-commit or pre-PR check
