# slop rules

slop ships **25 rules**, language-agnostic across 11 grammars. The authoritative,
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
- `structure.duplication` — Type-2 clone clusters
- `structure.dependency-cycles` — Acyclic Dependencies Principle (error)
- `structure.god-module`, `structure.runts` — module/package size boundaries
- `structure.rigidity`, `structure.uselessness` — Martin's distance from the main sequence
- `structure.call-islands`, `structure.redundancy` — intra-module topology (REVIEW)
- `structure.escape-hatches`, `structure.hidden-mutators`, `structure.sentinels` — type discipline

**Class**
- `class-shape` — the Chidamber–Kemerer suite (CBO/DIT/NOC/WMC), as an observation

**Lexical**
- `lexical.stutter` — a name restating its enclosing scope
- `lexical.verbosity` — names compensating for a missing namespace
- `lexical.sprawl` — a closed alphabet acting as an undeclared type (REVIEW)
- `lexical.imposters` — a parameter that is really a receiver (a class in hiding)
- `lexical.slackers` — a real cluster whose names don't align
- `lexical.hammers` — institutionalised catch-all vocabulary (observation)
- `lexical.cohesion` — a module foreign to its package's vocabulary (observation)

`imposters` / `slackers` are observations alone, and promote to a REVIEW verdict only when
an independent structural signal (clones or redundant siblings) corroborates the cluster.

**Whole-corpus signals** (observations)
- `vocabulary` — identifier token distribution (a Zipf near-invariant; deviation is the signal)
- `hotspots` — churn × complexity, Tornhill (2015)
- `orphans` — top-level symbols with no detected references

See [the configuration reference](../CONFIG.md) for thresholds and exemptions.
