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

12 rules across 8 categories. All enabled by default except `orphans`.

| Rule | What it catches |
|---|---|
| `complexity.cyclomatic` | Functions with too many paths (CCX > 10) |
| `complexity.cognitive` | Functions that are too hard to read (CogC > 15) |
| `complexity.weighted` | Classes with too much aggregate method complexity (WMC > 40) |
| `halstead.volume` | Functions with high information content (V > 1500) |
| `halstead.difficulty` | Functions with dense operator/operand reuse (D > 30) |
| `npath` | Functions with combinatorial path explosion (NPath > 400) |
| `hotspots` | Files that are complex AND frequently changed (14d window) |
| `packages` | Packages with poor design (D' > 0.7, Zone of Pain) |
| `deps` | Circular dependencies between modules |
| `orphans` | Unreferenced symbols (disabled by default) |
| `class.coupling` | Classes depending on too many others (CBO > 8) |
| `class.inheritance.depth` | Inheritance trees that are too deep (DIT > 4) |
| `class.inheritance.children` | Base classes with too many subclasses (NOC > 10) |

Most thresholds match their cited sources (McCabe 1976, Chidamber & Kemerer
1994, etc.). Three defaults diverge deliberately: `complexity.weighted`
(WMC 40 vs 1990s industry 50), `halstead.volume` (V 1500 vs SonarSource
1000), and `npath` (NPath 400 vs Nejmeh 1988's 200). See docs/CONFIG.md
for the rationale behind each divergence. All are configurable via
`.slop.toml`.
