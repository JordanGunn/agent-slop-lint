"""Structural metric kernels.

Numeric metrics computed from the shape of code: cyclomatic and
cognitive complexity, NPath, Halstead, Chidamber-Kemerer object-oriented
metrics, package-level instability and abstractness. Each kernel
consumes the atomic ``_fs`` / ``_ast`` primitives and emits per-file or
per-class records that the corresponding ``slop.rules.*`` wrapper
threshold-checks.
"""
