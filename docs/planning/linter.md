# Linter + Result + Violation

Status: Linter entry-point class, Result interface, and
Violation telemetry carrier are locked. Filter-parameter
shape and rule-side migration scope remain open.

Companion docs: `language.md` covers the grammar interface;
`codebase.md` covers the corpus orchestrator that Linter
composes.

## Scope of this document

What is settled:

- `Linter` is the entry-point class; it composes a `Codebase`
  and owns the rule loop. Module-level `run_lint()` retires.
- `Result` (peer to `Linter`, replacing `LintResult`) exposes
  `json()` and `pretty()` as its public formatting interface.
- `Violation` is the structured carrier for findings; future
  agent-facing corrective hints attach via Violation
  (`metadata` short-term; promote to a first-class `suggestion`
  field once the calibration taxonomy is settled).

What is NOT settled and is left for follow-up:

- Filter parameter shape on `Linter.run()` (today
  `filter_category=` and `filter_rule=`; preserve, rename, or
  refactor).
- `Result.json()` return type (dict vs. serialised str).
- Rule-side migration scope (how many rules port to the
  view-based signature in one intent).

---

## Locked: Linter as entry-point class

The module-level `run_lint(config)` function in `engine.py`
retires; `Linter` is the entry-point class.

```
Linter(config) ──▶ holds:
                    ├─ config        (loaded SlopConfig from config.py)
                    └─ codebase      (Codebase constructed from config primitives)

Linter.run(filter_category=, filter_rule=) ──▶ Result
    │
    └─ codebase.scan()         (one fd walk, one parse pass)
       │
       ▼
       for rule in selected_rules:
           rule.run(view, rule_config, config)   ← view: Structure or Lexicon
       │
       ▼
       apply waivers, aggregate counts, compute overall status
```

### Principles

- **Composition, not inheritance.** Linter has-a Codebase.
  Codebase has no knowledge of linting. A future consumer
  (`slop inspect`, a metrics-extractor, a test harness) can
  hold a Codebase without ever touching Linter.
- **Config is upstream.** `config.py` keeps the upward walk
  for `.slop.toml` / `pyproject.toml`. Linter takes a loaded
  `SlopConfig`; it doesn't load configs itself.
- **One Linter, one run, one Result.** Filtering by category
  or rule-name is a query on `Linter.run()`, not an entity
  split. A single corpus produces a single report.

### Module layout (target)

- `engine.py` becomes `linter.py` (class `Linter`).
- The category-agnostic helpers (rule selection, waivers,
  overall-status aggregation) stay as private module-level
  functions or migrate to methods on `Linter`. Decision is
  implementation-time, not design-time.
- The CLI calls `Linter(config).run()` instead of
  `run_lint(config)`.

---

## Locked: Result interface

`Result` (peer class to `Linter` in the linter module,
replacing the existing `LintResult` model) is the user-facing
report. One run, one Result, one verdict.

### Public surface

```python
result = linter.run()

result.json()      # canonical machine-readable representation
result.pretty()    # human-readable terminal output (replaces old "human" formatter)
```

Both methods are the entity's interface; implementations may
delegate to the formatter functions currently in `output.py`.
The entity owns the *what*; the formatter module owns the
*how*.

### What stays on the entity itself

- Run metadata: version, root, languages detected, display
  root.
- Per-rule results dict (keyed by rule name).
- Aggregate counts (violations, advisories, waived).
- Overall verdict (pass / fail / error → CI exit code).

### What does NOT split

The category split (`structural.Result` + `lexical.Result`) is
explicitly rejected at the output boundary. Category lives in
the rule-name prefix; filtering by category is a query, not
an entity split. If category-grouped accessors are useful for
ergonomics, they live as views (`result.by_category("lexical")`)
on the single Result, not as parallel Result entities.

### Future-format hook

Adding a third format (SARIF, JUnit XML, quiet) is an additive
change: either another method on Result (`result.sarif()`) or a
parameterised `result.format(style=)`. Cross that bridge when a
second non-JSON consumer arrives. `pretty(verbose=False)` is the
natural place for the current `quiet` formatter to absorb into.

---

## Locked: Violation as the agent-telemetry carrier

The Phase-6 calibration work will surface correspondences
between method-battery profiles and corrective actions (e.g.
imposters cluster with high body-Jaccard + zero receiver-call
density → "consider extracting a strategy family"; high
body-Jaccard + high receiver-call density → "consider
extracting a class"). These corrective hints are agent-facing
structured guidance, not just human prose.

`Violation` is already the structured carrier. No design
change is required today. The migration path:

1. Short-term: corrective hints attach as free-text under
   `Violation.metadata["suggestion"]`.
2. Once the calibration-derived taxonomy of corrective
   categories is settled, promote `suggestion` to a first-class
   field on `Violation` with an enum or constrained
   vocabulary.

The v2.0 substrate doesn't need to know what hints will
eventually exist; it only needs to keep `Violation` structured
enough to carry them, which it already is.

---

## Open — next rounds

### Rule-side migration scope

How many of the 9 lexical rules port in one intent. Sprawl,
slackers, and imposters benefit most from `Lexicon` slicing;
the rest might land as a separate intent. Engine-side refactor
(`rule.run(view, rule_config, config)` instead of
`rule.run(root, rule_config, config)`) is also its own scope —
the new signature can co-exist with the old for unported
rules during the migration window.

**Each port has two components** (per the views-own-compute
principle locked in `codebase.md`):

1. **Implement the view method(s) the rule needs.** For
   structural rules: `structure.cyclomatic(c)`,
   `structure.cognitive(c)`, etc. For lexical rules:
   `lexicon.body_signature(c)`, `lexicon.modal_tokens()`, etc.
   These compute methods are the durable artifact — once
   landed, every subsequent rule that needs the same metric
   reuses the implementation.
2. **Write the v2 rule wrapper.** Pure threshold-application
   + finding-emission. No AST walking, no tree-sitter import,
   no per-language branching. The rule receives a view and
   asks it for scalars.

Intent 11 (cyclomatic) therefore lands `Structure.cyclomatic()`
+ the v2 cyclomatic rule. Intent 12 (imposters) lands the
Lexicon compute methods for body-signature / receiver-call
density + the v2 imposters rule. Etc.

### Filter parameter shape on `Linter.run()`

Today `run_lint` accepts `filter_category` and `filter_rule`.
The new `Linter.run()` inherits these. Whether the parameter
names stay, fold into a single `filter=` argument with a
parsed shape, or become methods (`linter.with_category(...).run()`)
is an implementation-time call.

### `Result.json()` return type

Dict (caller controls serialisation) or string. Almost certainly
dict; currently `--output json` emits a serialised string at
the CLI layer. Cleanest split: `Result.json()` returns a dict,
the CLI serialises via `json.dumps()` at the output boundary.
