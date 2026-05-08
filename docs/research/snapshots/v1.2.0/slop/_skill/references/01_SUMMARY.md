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

24 rules across the `structural`, `information`, and `lexical` suites. All enabled by
default except `structural.orphans`.

| Rule | What it catches |
|---|---|
| `structural.complexity.cyclomatic` | Functions with too many paths (CCX > 10) |
| `structural.complexity.cognitive` | Functions that are too hard to read (CogC > 15) |
| `structural.complexity.npath` | Functions with combinatorial path explosion (NPath > 400) |
| `structural.class.complexity` | Classes with too much aggregate method complexity (WMC > 40) |
| `structural.class.coupling` | Classes depending on too many others (CBO > 8) |
| `structural.class.inheritance.depth` | Inheritance trees that are too deep (DIT > 4) |
| `structural.class.inheritance.children` | Base classes with too many subclasses (NOC > 10) |
| `structural.hotspots` | Files that are complex AND frequently changed (14d window) |
| `structural.packages` | Packages with poor design (D' > 0.7, Zone of Pain) |
| `structural.deps` | Circular dependencies between modules |
| `structural.local_imports` | Function-scoped import statements |
| `structural.redundancy` | Sibling functions sharing non-trivial callees |
| `structural.types.sentinels` | Str parameters with sentinel names (status, mode, etc.) |
| `structural.types.hidden_mutators` | In-place mutation of collection parameters |
| `structural.types.escape_hatches` | Overuse of escape-hatch types (Any, interface{}) |
| `structural.duplication` | Structurally identical function bodies |
| `structural.god_module` | Files with too many top-level definitions |
| `structural.orphans` | Unreferenced symbols (disabled by default) |
| `information.volume` | Functions with high information content (V > 1500) |
| `information.difficulty` | Functions with dense operator/operand reuse (D > 30) |
| `information.magic_literals` | Excessive magic numbers per function |
| `information.section_comments` | Excessive section-divider comments in functions |
| `lexical.stutter` | Identifiers repeating tokens from their enclosing scope |
| `lexical.verbosity` | Functions with overly verbose multi-token identifiers (mean > 3.0) |
| `lexical.tersity` | Overuse of very short (≤ 2 char) identifiers (guardrail) |

Most thresholds match their cited sources (McCabe 1976, Chidamber & Kemerer
1994, etc.). Three defaults diverge deliberately:
`structural.class.complexity` (WMC 40 vs 1990s industry 50),
`information.volume` (V 1500 vs SonarSource 1000), and
`structural.complexity.npath` (NPath 400 vs Nejmeh 1988's 200). See
`docs/CONFIG.md` for the rationale behind each divergence. All are
configurable via `.slop.toml`.

Pre-0.9.0 names (`complexity.cyclomatic`, `halstead.volume`, `npath`,
`hotspots`, `packages`, `deps`, `orphans`, `class.coupling`, ...) and their
matching `[rules.<old>]` TOML tables still work via a compatibility shim
that warns once at config-load time. The shim is removed in 1.0.0.
