"""slop.metrics — slop's measurements over the substrate.

An organizational umbrella over two independent families that share a *consumption
pattern*, not code:

- ``metrics.structural`` — structural metrics computed over ``ast`` nodes + the
  analysis-context (cyclomatic, Halstead, CK, Martin, clones, hotspots, orphans, …).
- ``metrics.lexical`` — slop's invented lexical *signals* composed over the
  ``slop.lexicon`` kernel (sprawl, stutter-overlap, hammers). Not a rename of the
  kernel: ``lexicon`` stays the standalone linguistic library; this is the slop layer
  above it. (Stood up when the lexical rules are ported.)

Metrics are *measurements*. Thresholds and verdicts live above, in ``linter``. A
metric takes plain inputs — an addressable region plus the corpus-global context —
never a scope object, so ``metrics`` never imports ``scope``.
"""
