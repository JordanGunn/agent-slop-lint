"""slop.metrics: measurements over the parsed code.

``metrics.structural`` computes structural measures over ``ast`` nodes and the corpus-wide
analysis context: cyclomatic, cognitive and NPath complexity, Halstead volume, CK, Martin's
package metrics, clones, cohesion, hotspots, literals. Words in identifiers are measured by
``slop.lexicon``.

Metrics measure; rules set the limits. A metric takes plain inputs (a region exposing its
nodes, and the context), never a scope class, so ``metrics`` never imports ``scope``.
"""
