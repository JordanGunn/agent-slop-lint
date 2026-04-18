"""Internal metric kernels used by slop rules.

This subpackage holds the tree-sitter, ripgrep, fd, and git kernels
that each rule in ``slop.rules`` wraps. It is shipped inside the
installed wheel; slop does not depend on any separate package for
metric computation. See the top-level NOTICE and LICENSE in this
directory for attribution of the code's original authorship.

Treat this tree as private. Names may move, return shapes may tighten,
and the package path may be restructured without notice. External
callers should use slop's public rule interfaces (``slop.rules``,
``slop.engine``) rather than importing from here.
"""
