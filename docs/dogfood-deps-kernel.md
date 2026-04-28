---
status: case_study
stability: current
ship_state: documentation only
purpose: record a dogfood finding from running slop against its former AUx dependency kernel and the corrective course selected
updated: 2026-04-28
---

# Dogfood Finding: `deps_kernel`

This note records a concrete dogfood finding from running `slop` against its
own source with the dogfood exclusions removed.

The normal repository config excludes the ported kernel/helper packages:

```toml
exclude = [
    "**/_fs/**",
    "**/_text/**",
    "**/_ast/**",
    "**/_compose/**",
    "**/_structural/**",
    "**/_util/**",
]
```

That exclusion is historically understandable: these packages were ported from
AUx and initially behaved like vendored implementation machinery. When scanned
without the exclusion, the kernel layer shows the structural concentration that
`slop` is designed to surface.

## Command

The finding below came from scanning the full `src` package with built-in
defaults rather than the repo-root dogfood exclusions:

```bash
cd src
uv run slop check complexity --config pyproject.toml --root . --no-color --max-violations 30
uv run slop check npath --config pyproject.toml --root . --no-color --max-violations 30
uv run slop check halstead --config pyproject.toml --root . --no-color --max-violations 30
```

## Scores

Before remediation, `cli/slop/_structural/deps.py:122 deps_kernel` reported:

| Rule | Score | Default threshold | Result |
|---|---:|---:|---|
| `complexity.cyclomatic` | 21 | 10 | fail |
| `complexity.cognitive` | 31 | 15 | fail |
| `npath` | 6048 | 400 | fail |
| `halstead.volume` | 2584 | 1500 | fail |
| `deps` | clean | no cycles | pass |

The important distinction is that the module is not architecturally tangled by
imports. The failure is local concentration: one function owns too many stages
of the dependency-analysis pipeline.

After remediation, the same function reports:

| Rule | Before | After | Default threshold | Result |
|---|---:|---:|---:|---|
| `complexity.cyclomatic` | 21 | 2 | 10 | pass |
| `complexity.cognitive` | 31 | 1 | 15 | pass |
| `npath` | 6048 | 2 | 400 | pass |
| `halstead.volume` | 2584 | 553 | 1500 | pass |

The first pass left one narrower dependency-kernel finding:

| Subject | Rule | Score | Default threshold | Result |
|---|---|---:|---:|---|
| `cli/slop/_structural/deps.py:498 _extract_go_imports_text` | `complexity.cognitive` | 17 | 15 | fail |

A second pass extracted the Go fallback parser into smaller predicates and edge
construction helpers:

| Subject | Rule | Before | After | Default threshold | Result |
|---|---|---:|---:|---:|---|
| `_extract_go_imports_text` | `complexity.cognitive` | 17 | 10 | 15 | pass |
| `_extract_go_imports_text` | `complexity.cyclomatic` | 9 | 6 | 10 | pass |
| `_extract_go_imports_text` | `npath` | 15 | 9 | 400 | pass |
| `_extract_go_imports_text` | `halstead.volume` | 505 | 285 | 1500 | pass |

The original public orchestration function is no longer the structural
bottleneck, and the remaining fallback parser hotspot was reduced below the
default thresholds.

## What The Highlighted Subject Looks Like

`deps_kernel` currently performs the full analysis pipeline in one public
function:

1. Discover files.
2. Build a stem-to-path module index.
3. Extract imports from every file.
4. Flatten import edges.
5. Resolve raw module strings to local files.
6. Build efferent adjacency.
7. Build afferent reverse adjacency.
8. Detect dependency cycles.
9. Resolve optional target mode.
10. Deduplicate raw imports.
11. Compute per-file Ca, Ce, and instability.
12. Sort, truncate, filter cycles, and return.

Each individual stage is reasonable. The problem is that all stages are fused
inside one function, so any change to import extraction, graph construction,
cycle reporting, target filtering, or result shaping requires editing the same
high-complexity body.

This is a typical agentic-port shape: functioning code, shallow tests,
reasonable comments, and too much responsibility in the first implementation
unit that happened to work.

## Interpretation

The linter finding is valid. This is not a false positive caused by an
irreducibly complex algorithm. The function is a pipeline, and the pipeline has
natural stage boundaries.

The finding also shows why the normal dogfood exclusion should not be treated
as a permanent clean bill of health. Excluding former AUx kernels keeps CI
stable while the kernels are being adopted, but ownership eventually requires
turning the structural checks back on and reducing the most concentrated
functions.

## Corrective Course

The selected corrective course was conservative:

1. Add characterization tests around current behavior.
2. Keep the public `deps_kernel` API unchanged.
3. Keep the implementation in one file; the issue is function-level
   concentration, not file-level incoherence.
4. Extract named private helpers for pipeline stages.
5. Avoid algorithm changes in the first pass.
6. Rerun `slop` against `deps_kernel` to confirm the public function's
   structural score improves.

The resulting shape is an orchestration function:

```python
def deps_kernel(...) -> DepsResult:
    discovered = _discover_dependency_files(...)
    if not discovered.paths:
        return _empty_result(...)

    graph = _build_dependency_graph(root, discovered.paths, language)
    target_abs = _resolve_target(root, target)
    file_deps = _build_file_deps(...)
    file_deps, truncated = _sort_and_cap_file_deps(file_deps, max_results)

    return DepsResult(...)
```

The helper boundaries are:

| Helper | Responsibility |
|---|---|
| `_discover_dependency_files` | wrap `find_kernel` and normalize discovered file paths |
| `_build_module_index` | build exact module-path and fallback stem resolvers |
| `_build_dependency_graph` | coordinate extraction, resolution, adjacency, cycles |
| `_resolve_edges` | convert raw import edges into raw imports and local efferent edges |
| `_reverse_adjacency` | build afferent map |
| `_resolve_target` | normalize target mode |
| `_unique_imports` | stable import deduplication |
| `_build_file_deps` | compute per-file Ca, Ce, instability |
| `_sort_and_cap_file_deps` | sort and truncate result records |
| `_filter_cycles` | apply target-mode cycle filtering |

## Verification

The remediation pass added characterization tests for the dependency kernel and
then reran the dogfood checks.

```bash
cd src
uv run python -m pytest tests/test_rules/test_dependencies.py
uv run python -m pytest
uv run slop lint --no-color
uv run slop check complexity --config pyproject.toml --root . --no-color --max-violations 80
uv run slop check npath --config pyproject.toml --root . --no-color --max-violations 80
uv run slop check halstead --config pyproject.toml --root . --no-color --max-violations 80
```

Results:

| Check | Result |
|---|---|
| Dependency characterization tests | 9 passed |
| Full test suite | 105 passed |
| Normal dogfood config | pass, no violations |
| Full-source complexity scan | `deps_kernel` no longer listed |
| Full-source NPath scan | `deps_kernel` no longer listed |
| Full-source Halstead scan | `deps_kernel` no longer listed |

## Second Pass

The first pass deliberately did not change cycle detection or module resolution
semantics. Those were handled in a second pass:

- Cycle detection now uses Tarjan SCC reporting, matching the rule
  documentation.
- Module resolution now prefers exact local module paths such as `pkg.service`
  or `pkg/service` before falling back to the historical last-component stem
  match.
- Go text fallback extraction now has characterization coverage for single-line
  imports, grouped imports, and aliased grouped imports.

The resolver is still intentionally best-effort. It does not implement full
language-specific import semantics, package manager resolution, or Python
namespace package behavior. Those belong in a larger dependency-analysis pass,
not in this corrective cleanup.
