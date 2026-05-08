# lexical.sprawl

**What it measures:** Closed-alphabet patterns where a set of values
recurs as a varying token across function-name templates within a
scope. Detects the "language alphabet" smell: `_python_extract`,
`_java_extract`, `_csharp_extract` — the alphabet `{python, java,
csharp}` is encoding a missing type.

**Default threshold:** flag clusters with `≥ 3` alphabet members and
`≥ 2` operations using that alphabet. Severity `warning`.

**Settings:**

| Setting | Default | Description |
|---|---|---|
| `min_alphabet` | `3` | Minimum alphabet size (closed-set values) |
| `min_concept_extent` | `2` | Minimum entities in a Formal Concept |
| `min_concept_intent` | `2` | Minimum operations in a Formal Concept |

## What it surfaces

Naming templates with one varying position drawn from a closed set
of values. The classic case:

```python
def _python_extract(node, content): ...
def _java_extract(node, content): ...
def _csharp_extract(node, content): ...
def _python_walk(tree, content): ...
def _java_walk(tree, content): ...
def _csharp_walk(tree, content): ...
```

The alphabet `{python, java, csharp}` appears as the varying token
across two operations (`extract`, `walk`). Formal Concept Analysis
(Wille 1982) over the entity × operation relation surfaces:

- The **inheritance lattice** — pairs `(parent, child)` where every
  operation the parent overrides is also overridden by the child.
- **Concepts** — maximal `(entity-set, operation-set)` pairs where
  every entity supports every operation. A concept is the
  candidate class with `n` instances and `k` methods.

## Recursive scoping

Detection runs at file scope first, then package, then root —
clusters are reported at the narrowest scope where they cohere.
A finding's metadata records its scope. Cross-package noise (the
same alphabet member appearing incidentally in unrelated places)
fails the coherence test and drops out.

## Method backing

Per `docs/methods/lexical/closed_alphabet_entity.md` and
`docs/methods/lexical/within_cluster_affix.md`. Citations:

- Caprile & Tonella (2000) — affix-pattern detection from token
  edit-distance
- Wille (1982); Ganter & Wille (1999) — Formal Concept Analysis

## Configuration

```toml
[rules.lexical.sprawl]
enabled = true
severity = "warning"
min_alphabet = 3
min_concept_extent = 2
min_concept_intent = 2
```

## Why "sprawl"

The same closed alphabet sprawls across many name positions. A
codebase without sprawl declares the alphabet as a type
explicitly; one with it embeds the alphabet in template positions
across files.
