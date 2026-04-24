# The defensible subset

Not every code smell can be metricized. Feature Envy, Mysterious Name,
Comments-as-Deodorant — these require human judgment of intent, not
structural analysis of form. The claim is not that every smell can be
reduced to arithmetic. The claim is that the computable subset is large
enough to do the work an agent needs done.

The research community has been building computable quality instruments
for decades. What follows is the subset that survives every constraint
that matters for agentic application: deterministic computation,
established literature, clear thresholds, language-agnostic semantics,
and — most importantly — computability from primitives that can be run
as external tooling without trusting the agent's account of its own
work.

## The metrics

| Metric | What it captures | Source | slop rule |
|---|---|---|---|
| Distance from the Main Sequence (D') | Architectural rot at the package level | Martin, 1994 | `packages` |
| Coupling Between Object Classes (CBO) | Over-coupling at the class level | Chidamber & Kemerer, 1994 | `class.coupling` |
| Depth of Inheritance Tree (DIT) | Fragile inheritance hierarchies | Chidamber & Kemerer, 1994 | `class.inheritance.depth` |
| Number of Children (NOC) | Downstream coupling from base classes | Chidamber & Kemerer, 1994 | `class.inheritance.children` |
| Weighted Methods per Class (WMC) | Aggregate method complexity per class | Chidamber & Kemerer, 1994 | `complexity.weighted` |
| Cyclomatic Complexity (CCX) | Path coverage burden at the method level | McCabe, 1976 | `complexity.cyclomatic` |
| Cognitive Complexity | Subjective reading difficulty | Campbell, 2018 | `complexity.cognitive` |
| Halstead Volume | Per-function information content (length × log₂ vocabulary) | Halstead, 1977 | `halstead.volume` |
| Halstead Difficulty | Per-function operator/operand density | Halstead, 1977 | `halstead.difficulty` |
| NPath | Per-function acyclic execution path count (multiplicative) | Nejmeh, 1988 | `npath` |
| Change coupling / hotspot density | Decay and defect risk over time | Gall et al., 1998; Tornhill, 2015 | `hotspots` |
| Acyclic dependency violations | Structural invariant violations | Lakos, 1996; Martin, 2002 | `deps` |
| Dead code / unreferenced symbols | Decay through accumulation | (widely tooled) | `orphans` |

## Why these and not others

Each metric in the table above earns its place by satisfying all five
criteria simultaneously:

1. **Deterministic.** Same input produces same output, regardless of who
   runs it. No subjective judgment required.

2. **Established.** Published in peer-reviewed venues or practitioner
   literature with decades of validation. Not novel, not experimental.

3. **Thresholded.** Clear, documented boundaries between acceptable and
   unacceptable values. McCabe's 10/20/50 thresholds for cyclomatic
   complexity have been standard since 1976.

4. **Language-agnostic.** Computable from AST traversal, dependency
   graphs, or git history — primitives available in every language with
   a tree-sitter grammar.

5. **Externally computable.** Can be run by tooling that exists outside
   the agent's control surface. The agent cannot influence the score.

## The academic lineage

These metrics are not new. They predate the smartphones used to praise
the AI tools that ignore them:

- McCabe published Cyclomatic Complexity in **1976** — three years
  before the first commercial spreadsheet.
- Halstead followed with Software Science in **1977**.
- Henry and Kafura formalized information flow complexity in **1981**.
- Parnas described software aging in **1994**. Martin formalized
  architectural rot in the same year. Chidamber and Kemerer published
  the object-oriented metrics suite in the same year.
- Gall, Hajek, and Jazayeri described change coupling in **1998**.

The entire catalogue predates the first AI coding assistant by more
than four decades. The field spent forty years building instruments
capable of measuring code quality with mathematical rigor. Then it
built systems capable of producing code at industrial scale. Then it
connected the two with a markdown file.

slop is an attempt to use the instruments.

## What is not included (and why)

**Halstead's derived measures: estimated bug count (B) and effort (E).**
Volume and Difficulty are included in the table above. The further
derivations Halstead proposed for estimating bug count and programmer
effort have weak empirical validation in modern contexts and are not
implemented.

**Response For a Class (RFC).** Part of the Chidamber & Kemerer suite
but requires call-graph resolution that tree-sitter alone cannot
provide reliably.

**Lack of Cohesion of Methods (LCOM).** Also C&K, but has known
methodological issues (negative values, no normalization) and at least
four named variants (LCOM2 through LCOM*). Requires a design decision
on which variant to commit to.

**Connascence (Page-Jones, 1996; Weirich, 2009).** A taxonomy of
coupling types, not a scalar metric. Partially manual, partially
tooled. Provides vocabulary rather than measurement. May be added as
a categorical classification in a future version.

---

*Adapted from "What Messy Actually Means" in "Agentic Smells" by
Jordan Godau. The defensible subset table and selection criteria are
from the original paper.*
