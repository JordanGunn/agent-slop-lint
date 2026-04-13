---
description: What slop is and what the agent needs to know.
index:
  - Identity
  - Rules
---

# Summary

## Identity

slop is an agentic code quality linter. It runs structural analysis rules
against a codebase and reports violations — complexity, coupling, churn
hotspots, dependency cycles, inheritance depth, and dead code. The metrics
are computed by external tooling (tree-sitter AST traversal, git history,
ripgrep); the agent cannot influence the scores.

slop is a CLI. The agent invokes it, reads JSON output, and decides what
to report to the user. The agent does not compute metrics itself.

## Rules

10 rules across 6 categories. All enabled by default except `orphans`.

| Rule | What it catches |
|---|---|
| `complexity.cyclomatic` | Functions with too many paths (CCX > 10) |
| `complexity.cognitive` | Functions that are too hard to read (CogC > 15) |
| `complexity.weighted` | Classes with too much aggregate method complexity (WMC > 50) |
| `hotspots` | Files that are complex AND frequently changed (90d window) |
| `packages` | Packages with poor design (D' > 0.7, Zone of Pain) |
| `deps` | Circular dependencies between modules |
| `orphans` | Unreferenced symbols (disabled by default) |
| `class.coupling` | Classes depending on too many others (CBO > 8) |
| `class.inheritance.depth` | Inheritance trees that are too deep (DIT > 4) |
| `class.inheritance.children` | Base classes with too many subclasses (NOC > 10) |

Thresholds are configurable via `.slop.toml`. The defaults are standard
academic thresholds (McCabe 1976, Chidamber & Kemerer 1994, etc.).
