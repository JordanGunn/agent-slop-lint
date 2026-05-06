# composition.affix_polymorphism

**What it measures:** Clusters of identifiers sharing a stem with
one token-position varying over a closed alphabet (e.g.
`_python_extract`, `_java_extract`, `_csharp_extract`). When the
same alphabet appears across multiple operations, the flat
function set encodes an implicit type × operation matrix — a
missing-namespace pattern. Formal Concept Analysis (Wille 1982)
reconstructs the inheritance lattice over the matrix, surfacing
candidate base / derived classes when one entity's operations are
a strict superset of another's.

**Default threshold:** flag clusters where the varying position
has alphabet size `≥ 3` and at least `≥ 2` operations are shared
across the alphabet. Severity `warning`.

**Settings:**

| Setting | Default | Description |
|---|---|---|
| `min_alphabet` | `3` | Minimum number of distinct values in the varying position. |
| `min_concept_extent` | `2` | Minimum entities (alphabet members) in a Formal Concept to flag. |
| `min_concept_intent` | `2` | Minimum operations shared by all entities in the Formal Concept. |

## What it surfaces

Per-language helper families that have outgrown the flat-function
shape:

```python
# ❌ flagged — alphabet {python, java, csharp, javascript, typescript}
# × operations {extract, walk, collect}
def _python_extract(node, content): ...
def _java_extract(node, content): ...
def _csharp_extract(node, content): ...
def _python_walk(tree, content): ...
def _java_walk(tree, content): ...
def _csharp_walk(tree, content): ...
```

The kernel reports two complementary things for each cluster:

1. **Inheritance pairs** — when entity A's operations strictly
   contain entity B's, A is a candidate child / specialisation of
   B. Surfacing this directly addresses the most common form of
   the missing-namespace pattern.
2. **Formal Concepts** — maximal (entity-set, operation-set)
   pairs where every entity supports every operation. A concept
   with `n` entities and `k` operations is a candidate class with
   `k` methods and `n` instances or subclasses.

## Verdicts and reception

This is an **advisory** rule. Three rounds of empirical evaluation
(see `docs/observations/composition/`) found that even when shown
inheritance candidates, agents systematically prefer free functions
backed by data tables over inheritance hierarchies. The rule's job
is to **surface** the option; whether to lift the family into a
class, a strategy table, or leave it flat is a downstream
architectural decision.

```toml
[rules.composition.affix_polymorphism]
min_alphabet = 3
min_concept_extent = 2
min_concept_intent = 2
severity = "warning"
```

## Prior art

- Wille, R. (1982). *Restructuring lattice theory: an approach
  based on hierarchies of concepts.* The original formulation of
  Formal Concept Analysis, the lattice machinery underlying the
  inheritance-pair detection.
- Caprile & Tonella (2000). *Restructuring program identifiers
  based on word usage and stop-word filtering.* Identifier-pattern
  restructuring; the predecessor of the affix-detection step.
- Bavota et al. *Methodbook: Recommending Move Method refactorings
  via Relational Topic Models.* Extract Class refactoring detection
  from co-occurrence signal — the same family of static-analysis
  signal this rule provides.

See [`docs/philosophy/composition-and-lexical.md`](../../philosophy/composition-and-lexical.md)
for the full methodology walkthrough.
