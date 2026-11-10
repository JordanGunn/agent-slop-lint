## Information-theoretic lexical metrics — Halstead reframed onto the lexicon (OPEN)

> **Status: open backlog.** A design *direction*, not a built feature. Tracked as
> mainline follow-ups under `int_97397f86`. Decision portion (Halstead not made a rule)
> is settled; the lexicon-entropy measure is to investigate.

### The premise

Halstead's `Volume = N · log₂(η)` (N total tokens, η distinct) is information-theoretic
but uses the **uniform / maximum-entropy** assumption: `log₂(η)` is the bits to index one
symbol *only if all η vocabulary items are equiprobable*. Real token distributions are
sharply skewed (Zipf), so true Shannon entropy

```
H = − Σ pᵢ log₂ pᵢ        (always H ≤ log₂(η), equality iff uniform)
```

is strictly lower. Halstead Volume systematically overstates information content by
ignoring the distribution it measures over. (Halstead `Difficulty`/`Effort`,
`(η1/2)·(N2/η2)`, are psychological-effort heuristics — not information theory at all.)

### Decision — Halstead not made a rule

`volume`/`density` are **not** ported as standalone rules. Volume is a code-size proxy
correlated with the complexity family (cyclomatic/cognitive/sloc); density is a weak gate.
The measures stay reachable on `Structure` (ungated). The information-theory *value* does
not live in a structural rule — it migrates to the lexicon.

### The opportunity — real Shannon entropy on the naming distribution

The lexicon is one step from real entropy: `TokenDistribution` already turns a freq map
into Zipf α/R²/hapax/head-concentration. Adding `H`, normalized entropy
(**evenness** = `H / log₂(distinct)`, scale-free), and perplexity (`2^H`) is ~2 lines over
the same counts.

**Crucial distinction — different vocabulary, different signal:**

| | vocabulary | what entropy measures |
|---|---|---|
| Halstead | program tokens (identifiers + literals + operators) | code **size** |
| Lexicon | identifier **word-tokens** (`getUserName` → get/user/name) | naming **diversity** |

So this is not "move Halstead to the lexicon" — it is the information-theoretic *idea*,
applied properly, becoming a naming-entropy measure Halstead never computed.

### Why it is not a rule

The identifier distribution is a **Zipf near-invariant** (see `distribution.py` and the
`lexical-distribution-invariance` memory) — "population norms, not quality dials." Global
naming-entropy inherits that: no honest scalar threshold, so no lint rule. If built, it is
a reported measure of `slop lexicon`, never a standalone rule.

The live signal is **normalized entropy at a *local* scope vs the corpus norm**:

- low evenness in a scope → repetitive naming
- high evenness + many word-types → a grab-bag vocabulary

Normalized scope-entropy is a candidate addition to the `vocabulary` narration, not a
rule on its own. That local-vs-corpus comparison, not raw entropy, is the thing to
investigate.
