# Body shape signatures

**Status:** Active in v2 PoC battery; promotion to kernel pending.
**PoC:** [`scripts/research/composition_poc_v2/poc2_body_shape.py`](../../../scripts/research/composition_poc_v2/poc2_body_shape.py)

## Problem

Two functions can share a first parameter and have nothing else
in common. Two functions can share a first parameter and be
literal copies of each other. Those are very different findings,
calling for very different review actions, and the cluster's
*name structure* doesn't distinguish them.

The single most consequential question once you have a cluster is:
"Are these functions doing the same thing parametrically, or are
they doing different things on the same input?" Body shape answers
that.

## Signal purpose

For a cluster of N functions, body shape produces a single
**mean pairwise Jaccard similarity** score over AST-node-type
3-grams. The score sits in [0, 1].

Reading the score:

| Score | Reading | Implication |
|---|---|---|
| ~1.0 | Type-2 clones; bodies are structurally identical | Strong tabular dispatch / strategy family. Either dispatch via data or accept as free functions. NOT extract a class with these as methods doing different work. |
| 0.5 - 0.9 | Moderate similarity; bodies share most structural elements | Family of related implementations. Could be base-class candidate (real shared algorithm) or family of helper variants. Other probes disambiguate. |
| 0.2 - 0.5 | Low similarity; bodies share scaffolding but do different work | Heterogeneous cluster. If receiver-call density is also high, this is the *real* "missing class" case (methods doing different jobs on the same receiver). |
| < 0.2 | No structural similarity beyond AST noise | Cluster shares input incidentally; very weak signal for any refactor. |

The score's discriminative power is at the extremes. A 1.00 score
is a hard veto on "extract a class with these as different
methods" — they aren't different methods, they're the same code.
A < 0.2 score is a hard veto on "extract a base class" — there's
no shared algorithm to lift.

## Algorithm

```
for each function in cluster:
    sig = []
    DFS(function.body):
        if node.type not in LEAF_OR_NOISE_SET:
            sig.append(node.type)
    ngrams[function] = set of 3-grams over sig

mean_jaccard = mean over all pairs (f, g):
    |ngrams[f] ∩ ngrams[g]| / |ngrams[f] ∪ ngrams[g]|
```

`LEAF_OR_NOISE_SET` excludes leaf identifiers, literals, and
punctuation tokens. The signature captures the *structure* of the
body (call → call → return, or if → for → call, etc.) without
sensitivity to identifier names or specific values. This is
deliberate: it's the same normalization that defines Type-2 clones
in the literature.

The choice of n=3 is empirical. n=2 is too permissive (any two
functions with a `call → return` pattern register as similar);
n=4 is too strict (bodies that are similar but not identical lose
all overlap). slop's existing `structural.duplication` rule uses
the same range.

## Citations

- **Roy, C.K., Cordy, J.R. & Koschke, R. (2009).** "Comparison and
  evaluation of code clone detection techniques and tools: A
  qualitative approach." *Science of Computer Programming* 74(7),
  470-495.
  The canonical survey of clone-detection techniques. Defines the
  Type 1 / Type 2 / Type 3 / Type 4 taxonomy. AST-based detection
  is the family of techniques this method draws from.

- **Baxter, I.D., Yahin, A., Moura, L., Sant'Anna, M. & Bier, L.
  (1998).** "Clone Detection Using Abstract Syntax Trees."
  *Proceedings of the International Conference on Software
  Maintenance*, 368-377.
  The foundational paper for AST-based clone detection. Establishes
  the principle that structural normalization (ignoring leaf
  identifiers) detects parametric duplication.

- **Tairas, R. & Gray, J. (2009).** "Phoenix-based Clone Detection
  using Suffix Trees." *Proceedings of the 47th Annual Southeast
  Regional Conference.*
  Variant on the AST-clone-detection family using suffix trees.
  Cited for completeness; we use n-gram Jaccard, which is simpler
  and sufficient for cluster cohesion (vs. corpus-wide clone
  finding).

## Modifications

- **Scope.** Standard clone detection runs corpus-wide and reports
  matched pairs. We run it within an already-detected first-
  parameter cluster and report a single cohesion score.
- **Output: Jaccard, not edit distance.** Roy/Baxter typically
  report tree-edit-distance or hash-collision counts; we report
  set Jaccard over n-grams. Jaccard is faster and produces a
  bounded [0, 1] score that's easier to threshold against.
- **No clone-class clustering.** Standard clone detection groups
  matching pairs into transitive clone classes; we don't, because
  the cluster is already given.

## ELI5

Squint at the function bodies — not the names, not the parameters,
just the shape of the code:

```python
def red(text):
    return _wrap("31", text)

def green(text):
    return _wrap("32", text)
```

These have the same shape. Not just similar — *literally identical*
once you ignore the literal "31" vs "32". One is a copy of the other
with a single value swapped. That's a Type-2 clone in the literature,
and the slop method assigns this pair a Jaccard of 1.00.

Now compare:

```python
def format_human(result):
    lines = []
    for category in result.categories:
        lines.append(...)
        for rule in category.rules:
            ...
    return "\n".join(lines)

def format_json(result):
    return json.dumps({"categories": [c.to_dict() for c in result.categories]})
```

Both take the same input. Both return a string. But the bodies look
nothing alike. One has a loop and string concatenation; the other
has a one-liner with a JSON dump. Jaccard is low (~0.12).

The interpretation differs:

- **High Jaccard:** "These are the same thing N times — pull the
  varying part out into a data table or a strategy class. Don't
  make these different methods of one class — they're not different
  methods, they're the same method."
- **Low Jaccard:** "These are doing different things that happen to
  share input. If they belong together at all, it's because the
  input is a receiver, and they're the methods. Other probes need
  to confirm the receiver hypothesis."

Body shape doesn't tell you the answer. It tells you which of the
two questions you're working on.
