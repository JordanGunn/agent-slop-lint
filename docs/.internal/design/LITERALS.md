## Literal-management battery — OPEN INVESTIGATION (backlog, not a settled design)

> **Status: open backlog.** This captures a design *vision*, not a committed design.
> The core question — *which of these signals combine into a precise battery* — is
> unanswered. Tracked as explicit mainline follow-ups under `int_2088e44a`.

### Decision

`magic_literals` **stays** in v3 (it is not cut as borderline-style), but a bare
per-body magic-literal *count* is **not shippable alone**. A count flags a style nit
agents self-correct; the real slop is structural and the count cannot express it. So
the rule is kept as the *seed* of a literal-management battery, and the port is
deferred until the complementary signals below are designed.

### Thesis

Managing literals in agentic code is slop along three axes a count misses:

1. **Bidirectional** — not just "literal with no constant" (missing-def) but also
   "constant/enum defined and never used" (dead-def). Agentic code exhibits the
   inverse — minting defs it never wires up — more than human code does.
2. **Mechanism selection** — the right representation depends on the literals'
   relationships: a recurring *cluster* of related literals wants an **enum** (where
   the language supports it); an *isolated* repeated literal wants a **constant**;
   literals used only within one class want **class constants/vars**, not bare
   literals in method bodies.
3. **Placement** — *where* the shared def should live, weighted by the literal's
   **sprawl** (dispersion across the corpus), and constrained by **DIP**. The classic
   slop move is minting a *local* constant without checking one already exists; the
   fix is to find the correct shared home, not to duplicate.

Plus a cheap positional signal: constants/literals should be declared at the **top**
of their scope, not scattered.

### The five follow-up signals (tracked under `int_2088e44a`)

| Signal | Note |
|---|---|
| Bidirectional def↔use coverage | missing-def + dead-def. Relates to `orphans`. The seed signal. |
| Mechanism: enum vs constant | recurring cluster → enum; isolated repeat → constant. **⚠ prior art** |
| Class-scoped literals → class constants | class-ownership filter over literal usage. |
| DIP-aware shared-home placement (sprawl-weighted) | locate, don't duplicate. **⚠ prior art** |
| Declaration position | top-of-scope; cheapest, likely highest-precision. |

### Prior art that bounds two of these (do not re-tread)

- **enum selection** is adjacent to the **`changelings`** rule (raw-literal ==
  enum-value matching), which was **built then removed** for low precision — homonyms
  (keywords, zone labels, field names) inflated false matches. Do not rebuild the enum
  side without a semantic *reference-vs-coincidence* discriminator.
- **placement / DIP** is the **relocation** dimension, recorded as a **dead end**:
  orthogonal to every existing rule, and precision-capped by tree-sitter's approximate
  call resolution. Full Martin I×A is the layer model but sat below the shipping bar.
  Re-attempt only with that caveat.

### The open question

Which of these signals **combine** into a battery precise enough to ship? Individually
several are noisy (the count; naive enum-matching; relocation). The battery hypothesis
is that their *intersection* is the real signal — e.g. a repeated literal that is
(isolated) + (sprawled across N packages) + (no existing constant) is a confident
shared-constant verdict, where any one signal alone is not. That intersection is the
work to investigate before any of this ports.
