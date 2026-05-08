# Multi-criteria ranking

**Status:** Active in v2 PoC battery; promotion to kernel pending.
**PoC:** [`scripts/research/composition_poc_v2/poc6_multi_criteria_rank.py`](../../../scripts/research/composition_poc_v2/poc6_multi_criteria_rank.py)

## Problem

A first-parameter cluster reports N members. The N members are
not all equally strong examples of whatever the cluster represents.
Some are central — they actively use the parameter as a receiver,
their bodies look like their siblings', their names share the
cluster's modal vocabulary. Others are peripheral — they happen to
take the same parameter but don't use it as a receiver, their bodies
do unrelated work, their names share no tokens with the family.

Without a per-member fitness score, the linter can't:

- Distinguish "this 5-function cluster is really 4 functions in a
  family plus 1 outlier."
- Tell the user which member is the **canonical** representative
  to read first when investigating the cluster.
- Surface a partial-cluster diagnosis ("4 of 5 fit; the 5th is
  unrelated; review whether the cluster is real or whether one
  member should be moved").

This method computes a per-member fitness score combining three
criteria and ranks cluster members.

## Signal purpose

For each member of a cluster, three sub-scores in [0, 1]:

1. **Body-shape similarity** — mean Jaccard of this member's AST
   3-grams against all other members. (Same primitive as
   [body_shape_signatures](body_shape_signatures.md), but per-pair.)
2. **Receiver-call density** — count of `first_param.attr` and
   `first_param[key]` accesses in this member's body, normalized.
   Functions that actually treat the parameter as a receiver score
   high; functions that just store it or pass it along score low.
3. **Modal-token overlap** — fraction of this member's name tokens
   that overlap with the cluster's most-frequent tokens (top 3
   modal). Functions whose names match the family vocabulary
   score high.

Combined score (weights chosen empirically):
```
score = 0.4 * body_similarity + 0.4 * min(receiver_density / 10, 1.0) + 0.2 * modal_overlap
```

Sorting cluster members by score gives a **ranked list** with the
canonical member on top and the marginal member on the bottom.
The score *spread* across the cluster is itself diagnostic:

| Spread (top - bottom) | Reading |
|---|---|
| < 0.2 | Cluster is uniform; all members equally strong/weak |
| 0.2 - 0.4 | Cluster is moderate; some members stronger but no clear outliers |
| > 0.4 | Cluster is heterogeneous; weak members may not belong |

The receiver-call density component is the most diagnostic single
sub-score for the "extract a class" verdict. If most members of a
cluster have zero receiver-calls (they take `text` but never call
`text.method()`), the cluster is not a missing receiver class —
it's a strategy or transform family.

## Algorithm

```
for each cluster:
    members = cluster.members
    sigs = {m: ngrams_3(ast(m.body)) for m in members}
    name_tokens = [tokens(m.name) for m in members]
    flat = flatten(name_tokens)
    modal_tokens = top 3 by frequency in flat

    for each member m:
        body_sim = mean(jaccard(sigs[m], sigs[other])
                        for other in members - {m})

        receiver_calls = count of `cluster.param_name.x` accesses in m.body
                         + count of `cluster.param_name[k]` accesses in m.body
        receiver_density = receiver_calls / max(1, |sigs[m]| / 100)

        my_tokens = tokens(m.name)
        modal_overlap = |my_tokens ∩ modal_tokens| / |my_tokens|

        score[m] = 0.4 * body_sim
                 + 0.4 * min(receiver_density / 10, 1.0)
                 + 0.2 * modal_overlap

ranked = sorted(members, key=score, descending)
```

## Citations

- **Tsantalis, N. & Chatzigeorgiou, A. (2009).** "Identification of
  Move Method Refactoring Opportunities." *IEEE Transactions on
  Software Engineering* 35(3), 347-367.
  Multi-criteria ranking of Move Method opportunities. The exact
  scoring formula in Tsantalis/Chatzigeorgiou differs from ours
  (they use entity-set distance metrics on attribute access
  patterns), but the *style* — combine multiple objective signals
  per refactor candidate, then rank — is what we draw from.

- **Bavota, G., De Lucia, A., Marcus, A. & Oliveto, R. (2010).** "A
  two-step technique for Extract Class refactoring." *Proceedings
  of the 25th IEEE/ACM International Conference on Automated
  Software Engineering*, 151-154.
  Multi-objective Extract Class refactoring. Combines structural
  and semantic similarity into a single score per candidate.

- **Fokaefs, M., Tsantalis, N., Stroulia, E. & Chatzigeorgiou, A.
  (2009).** "Identification and Application of Extract Class
  Refactorings in Object-Oriented Systems." Journal of Systems and
  Software 85(10), 2241-2260.
  JDeodorant's Extract Class detection. Uses agglomerative
  clustering on a method-attribute access graph; each candidate
  cluster is scored by cohesion. Different signal source from our
  method but same multi-criteria scoring philosophy.

## Modifications

- **Three criteria, not five.** Tsantalis/Chatzigeorgiou's MOORA-style
  scoring uses more criteria including coupling-to-target-class and
  cohesion-with-source-class. We use three (body similarity,
  receiver-call density, modal-token overlap) because (a) we don't
  have a target class to score coupling against — we're proposing
  the class, not moving members between existing ones; (b) cohesion
  measurement requires per-member attribute-access tracking we
  haven't implemented; (c) the three criteria we have empirically
  produce reasonable rankings on slop's corpus.
- **Receiver-call density via attribute/subscript access.** This
  is our specific operationalization of "does this function treat
  the first parameter as a receiver?" — count `param.attr`
  expressions and `param[key]` subscripts. The literature uses
  more sophisticated definitions (e.g. attribute-access graphs);
  ours is simpler and runs from a single AST walk.
- **Score weights are heuristic.** `0.4 / 0.4 / 0.2` was chosen so
  that body similarity and receiver behavior dominate, with name
  overlap as a tiebreaker. Cross-corpus calibration is needed.
- **MOORA naming.** Tsantalis/Chatzigeorgiou's specific scoring
  method may or may not be named MOORA in their paper; I've called
  this method "Tsantalis-style" rather than MOORA pending citation
  verification. The multi-criteria ranking principle is what
  matters; the specific name is a citation-cleanup task.

## ELI5

You have a cluster of five functions all taking `result` as their
first parameter. You want to know which ones really belong in the
cluster and which are along for the ride.

For each function, ask three questions:

1. **Does this function look like its siblings?** Compare its body
   shape (the AST structure, ignoring identifier names) against
   every other member. If the bodies are similar, score 1; if they're
   completely different, score 0.

2. **Does this function actually use the parameter?** Count the
   number of times the function accesses `result.something` or
   `result[something]`. A function that does `result.violations`,
   `result.summary`, `result.errors` over and over is treating
   `result` as a receiver. A function that takes `result` and just
   passes it to another function isn't.

3. **Is this function's name in the family?** Look at the most
   common tokens across all the cluster's names — say `format`,
   `category`, `render`. If your function's name shares those
   tokens, you're probably in the family.

Combine the three answers (40/40/20 weight) and you get a single
score per function. Sort the cluster by score.

The top-scoring member is the canonical example — the function
that most behaves and is named like the cluster says it should.
The bottom-scoring member is the marginal one — it took the same
parameter but doesn't really fit.

If the spread between top and bottom is small, the cluster is
uniform: refactor decisions apply to all members equally. If the
spread is large, the cluster is mixed: investigate whether the
weak members actually belong, or whether they should be moved out.

The receiver-call signal alone is also useful as a hard test: if
ALL members have zero receiver-calls, the cluster is **not** a
missing receiver class. They take the parameter but don't act on
it as a receiver. This catches the strategy-family false positive
that the v1.1.0 single-signal rule produced for `color.py`.
