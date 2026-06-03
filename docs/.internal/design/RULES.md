## Rule Targeting Model (validation centerpiece)

Each rule declares the entity kind it targets, and each metric resolves to
exactly one home altitude. This table is how we validate the interface: if every
existing rule maps cleanly onto a kind without inventing scope strings, the spine
holds.

```text
complexity.cyclomatic / cognitive / npath / volume   -> Callable (aggregated upward; summed at every container)
WMC                                                   -> NOT a metric: weighting family. weight=cyclomatic => class.cyclomatic(); weight=1 => method_count()
god_module                                            -> Module
ck.* (dit, noc, cbo, lcom, nom)                       -> Class        (OO capability)
rigidity / instability / uselessness / abstractness   -> Package
deps / cycles                                         -> DependencyGraph
hotspots                                              -> Corpus/Module (+ git churn)
redundancy / clones                                   -> Module
call-islands (legacy "confusion", structural)         -> Module
lexical concept-dispersion (the user's "confusion")   -> any-altitude lexicon (hapax residual vs Zipf baseline, maturity-gated)
stutter / imposters / slackers / sprawl               -> SymbolContainer / Package lexicon
vocabulary                                            -> any-altitude lexicon (Realm/Package/Module/Class)
```

Rule output may still expose a string `scope` for human and machine consumers,
but internally the target is an entity kind with identity.

## Finding Ontology

A finding has two **orthogonal** axes. Collapsing them (the legacy mistake) loses
the most-used cell — the prescriptive-but-non-gating warning.

**Disposition (epistemic — what slop claims):**

- **Verdict** — a defect reverse-engineered from sloppy code: the action is agreed
  and the fix is prescribable deterministically. Carries a `prescription`.
- **Observation** — a claim-free empirical nudge ("look here; this may be a symptom
  of something larger"). Carries `evidence`, no prescription. Used where a
  measurement is informative but no remedy can be honestly prescribed (e.g. the
  token distribution is a Zipf near-invariant, so no scalar threshold is honest). An
  observation makes no precision claim, so it *cannot* be a false positive.

**Severity (operational — what it does to the build):** `error` (exit 1) > `warning`
(advisory) > `info` > `off`. A separate dimension layered on disposition.

**Coherence invariants (enforced by type, not runtime-validated):**

- Observation ⟹ severity `info`, action `INVESTIGATE`, no prescription, carries
  evidence. (A build failure is itself a precision claim; an observation makes none,
  so it cannot gate.)
- Verdict ⟹ severity `warning|error`, carries a prescription, no evidence.
- `Verdict` and `Observation` are **distinct types** sharing a `Finding` protocol —
  *not* one dataclass with a disposition discriminator and half-inert optional
  fields. Illegal states are unrepresentable by construction.

**The `REVIEW` action** is a verdict whose remedy is deferred: slop is confident the
structure is anomalous, but the fix is disjunctive and depends on a judgment slop
does not make (e.g. disjoint call-islands — split, or intentional facade?). It is a
verdict, not a third disposition; the conditionality lives in the action. slop does
**not** adjudicate intent — that is a separate concern. `REVIEW` verdicts **cap at
`warning`** (never `error`/exit-1): if we cannot prescribe the fix, we do not
hard-fail the build on it — the same logic that pins observations to `info`, one
tier up.

`confidence` is a verdict-internal scalar (how sure the prescription applies), not a
third axis; an observation has no prescription, so confidence is inert. A
sub-floor-confidence verdict is better demoted to an observation.

## Rule Dispatch and Scope

Scope is **navigable altitude**, not a string tag. Because `ast()` and `lexicon()`
exist on every component (see Per-Entity Projections), a metric is projectable at
any altitude, and the altitudes nest. This unlocks asking the same question at
different scopes — token repetition within one Callable vs. across a whole Package —
which the legacy flat views could not express cleanly.

**Dispatcher-driven, not rule-driven.** A rule *declares* the altitude(s) it is
defined at; the dispatcher walks the component tree and invokes the rule at every
component of that altitude:

```text
for kind in rule.altitudes:
    for component of that kind in corpus:
        rule.check(component, config)     # dispatcher asserts >0 components visited
```

A rule never walks the corpus itself. Two consequences:

- **The silent-no-op bug class becomes unrepresentable.** A rule runs only where it
  declares itself defined, and the dispatcher asserts it visited >0 components — the
  "enabled-but-zero-checked" safeguard is now the dispatch invariant, not a bolt-on.
  The legacy failure (config keyed by category not name, so a rule silently checked
  nothing) cannot recur.
- **Altitude is a false-positive discriminator.** A token dense across a Package is
  domain vocabulary; the same token dense inside one Callable is slop. The signal's
  altitude *profile* corroborates it. (Cross-altitude suppression — mute a
  low-altitude verdict when a higher-altitude observation explains it — is research
  downstream of this spine, not a prerequisite for the executable.)

Declared altitudes mirror the targeting table above: complexity at
`{Callable, Class}`, CK at `{Class}`, Martin at `{Package}`, god_module at
`{Module}`, lexical dispersion scope-polymorphic at `{Class, Module, Package}`,
cross-cutting (hotspots/cycles) at `{Corpus}`.