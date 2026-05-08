---
description: Noise prevention and reporting discipline.
index:
  - Prohibitions
  - Reporting limits
  - Config management
---

# Policies

## Prohibitions

The agent MUST NOT:
- Paste raw slop JSON or CLI output into the conversation
- Explain what a metric IS unless the user asks ("McCabe's Cyclomatic
  Complexity measures..." — no)
- Use slop results to justify refactoring the user did not ask for
- Run slop repeatedly in one conversation without being asked
- Report a clean result in passive mode (silence IS the report)
- Editorialize beyond what the interpretation field provides
- List every violation — summarize, then offer detail on request

## Reporting limits

**Passive mode:**
- One sentence maximum. Count + worst offender + offer.
- Example: "slop found 3 complexity violations in files I touched —
  `dispatch` (CCX 24) is the worst. Want me to look at these?"

**Active mode:**
- One line per category that has violations (count + top offender).
- One line for clean categories (just the category name + "clean").
- Skip disabled categories entirely.
- Maximum 3 violations surfaced per category. If more exist, state the
  count.

## Config management

If no `.slop.toml` exists in the project root when slop is invoked:
1. Run `slop init` to generate the default config
2. Mention this to the user: "Generated .slop.toml with default thresholds."
3. Proceed with the lint run

Do not modify an existing `.slop.toml` without the user's approval.
