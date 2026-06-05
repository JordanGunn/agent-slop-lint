"""Structural metrics — measurements over AST shape + the analysis-context.

The relocated metric inventory: the result records (``records``) and the compute
(``complexity``, ``halstead``, ``callable_measures``, ``annotations``, ``class_index``,
``relational``, ``orphans``, ``hotspots``). Compute takes plain ``ast`` nodes (or a
duck-typed region) — never a scope/component object — so this package depends only on
``ast`` + ``identity`` + its own ``records``, and ``scope`` is free to depend on it
without a cycle.

``ast`` is the structural substrate; there is no separate structural *kernel* (these
metrics have no out-of-linter reuse story to justify one), which is the asymmetry with
the lexical side, where ``lexicon`` is a kernel beneath ``metrics.lexical``.
"""
