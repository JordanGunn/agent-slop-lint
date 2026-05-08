"""Cross-tool composition primitives.

Kernels that combine the atomic ``_fs`` / ``_text`` / ``_ast`` primitives
(plus git, where relevant) into higher-level data products: symbol
cross-references, churn-weighted hotspots, dead-code candidates. Sit
beneath the rule wrappers in ``slop.rules`` and beneath the metric
kernels in ``slop._structural``.
"""
