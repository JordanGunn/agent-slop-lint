"""Structural metrics: measurements over AST shape and the analysis context.

``records`` holds the frozen results; one module per measure computes them (``complexity``,
``halstead``, ``literals``, ``clones``, ``cohesion``, ``class_index``, ``hotspots``), and
``view.Structure`` is how rules and commands read them. They take ``ast`` nodes or a
duck-typed region, never a scope class, so ``scope`` can depend on this package without a
cycle.
"""
