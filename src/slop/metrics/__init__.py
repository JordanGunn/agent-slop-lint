"""slop.metrics — slop's measurements over the substrate.

- ``metrics.structural`` — structural metrics computed over ``ast`` nodes + the
  analysis-context (cyclomatic, Halstead, CK, Martin, clones, hotspots, orphans, …).

Vocabulary analysis lives in the standalone ``slop.lexicon`` kernel, not here. The
former ``metrics.lexical`` package held slop-invented signals and was removed; see
CHANGELOG for the commit it can be recovered from.

Metrics are *measurements*. Limits live above, in the rules. A
metric takes plain inputs — an addressable region plus the corpus-global context —
never a scope object, so ``metrics`` never imports ``scope``.
"""
