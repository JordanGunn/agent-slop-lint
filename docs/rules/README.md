# slop rules

slop ships **12 rules**, language-agnostic across 11 grammars. The authoritative,
always-current reference is the tool itself:

```bash
slop rules     # name, disposition, altitude for every rule
slop schema    # the exact config shape (thresholds + params), generated from the registry
```

Each rule's rationale — what it measures, why, the citation, and why it carries the
disposition it does — lives in its **module docstring** under `src/slop/rules/<name>.py`.
That is the single source of truth; this page is only a map (per-rule prose pages were
retired in v3 because hand-maintained copies of a docstring are exactly the drift slop
flags).

## Disposition

Every finding is one of three strengths, chosen by how confidently slop can speak:

- **Verdict** — a defect with a prescribed fix. Error-severity verdicts fail the build.
- **REVIEW** — the structure is anomalous but the remedy is a judgment slop won't make
  (warning-capped; never fails the build).
- **Observation** — a claim-free, evidence-backed nudge where no fix is honestly
  prescribable. It makes no precision claim, so it cannot be a false positive.

## The rules

**Complexity** (per callable, error verdict)
- `complexity.cyclomatic` — McCabe (1976)
- `complexity.cognitive` — Campbell (2018)
- `complexity.combinatorial` — NPath, Nejmeh (1988)

**Structure**
- `structure.god-module` — module size boundaries
- `structure.duplication` — Type-2 clone clusters
- `structure.dependency-cycles` — Acyclic Dependencies Principle (error)
- `structure.rigidity`, `structure.uselessness` — Martin's distance from the main
  sequence (REVIEW)

**Class**
- `class-shape` — the Chidamber–Kemerer suite (CBO/DIT/NOC/NOM), as an observation

**Whole-corpus signals**
- `vocabulary` — identifier token distribution (a Zipf near-invariant; deviation is
  the signal) (observation)
- `hotspots` — churn × complexity, Tornhill (2015) (observation)
- `orphans` — top-level symbols with no detected references (observation)

See [the configuration reference](../CONFIG.md) for thresholds and exemptions.
