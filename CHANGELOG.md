# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.1] - 2026-04-18

**Released to PyPI** on 2026-04-18 as `agent-slop-lint==0.6.1`. Tag: [`v0.6.1`](https://github.com/JordanGunn/agent-slop-lint/releases/tag/v0.6.1).

### Fixed

- **Bundled agent skill's `validate` command** (`skill.sh` / `skill.ps1`, installed via `slop skill <dir>`) used to fail on every slop-only install with `error: aux not found` and tell users to run `./scripts/install.sh`. The `aux` binary is not installed by `pip install agent-slop-lint` and was not a runtime dependency of slop post-0.5.0, so this was a broken instruction. `validate` now checks for `slop` only and points users at `pip install agent-slop-lint` or the install script.
- **`orphans` rule JSON output.** The `next_steps.verify_command` field used to emit `aux usages <symbol> --root <root>`, referencing a command slop does not ship. Replaced with `rg <symbol> <root>` (ripgrep is already a required slop system dependency). The accompanying `message` string now mentions "trace with ripgrep" rather than "trace with `aux usages`".
- Rule-file module docstrings (`complexity.py`, `class_metrics.py`, `dead_code.py`, `dependencies.py`, `hotspots.py`) and `preflight.py` no longer describe their kernels as "aux X_kernel"; they now say "the vendored X_kernel" to match post-0.5.0 reality.
- `docs/SETUP.md` troubleshooting entry for missing system tools no longer references `aux doctor` or `aux curl`; it points at `slop doctor` and a direct install hint for the three system binaries slop uses.

## [0.6.0] - 2026-04-18

**Released to PyPI** on 2026-04-18 as `agent-slop-lint==0.6.0`. Tag: [`v0.6.0`](https://github.com/JordanGunn/agent-slop-lint/releases/tag/v0.6.0).

### Added

- **`packages` rule now runs on every language slop supports.** Previously `packages` (Martin's Distance from the Main Sequence) was Go and Python only. The underlying `robert_kernel` now has abstract/concrete type detection for Java (`interface`, `abstract class`, `record`), C# (`interface`, `abstract class`, `struct`, `record`), TypeScript (`interface`, `abstract class`), Rust (`trait`, `struct`, `enum`), and JavaScript (all classes counted concrete because the language has no abstract/interface construct). Both the tree-sitter AST path and the regex fallback are implemented per language. See CONFIG.md for per-language semantics and the JavaScript "Zone of Pain by default" caveat.

### Changed

- Documentation cleanup. Removed every remaining claim that `slop` depends on the external `aux-skills` package at runtime (it does not since 0.5.0). README's "Architecture" section now describes the kernels as shipped inside the wheel. SETUP.md no longer says `pip install agent-slop-lint` pulls in `aux-skills`. CLAUDE.md rewritten along the same lines. NOTICE's stale "COMPUTATIONAL BACKEND" block removed and the vendor-code path updated to reflect the 0.5.0 restructure. `_aux/util/doctor.py` install hints for `tree-sitter` and `git` now point at `agent-slop-lint` and `slop hotspots` respectively rather than the pre-vendor `aux-skills` and `aux delta`. Optional-Python-packages block (for the aux curl kernel, which slop does not ship) removed. `_aux/__init__.py` docstring reworded to describe what the subpackage is; attribution remains in NOTICE and the vendored LICENSE where Apache 2.0 requires it.
- Language support table in README and SETUP.md updated to mark `packages` as `yes` for Java, C#, TypeScript, JavaScript, and Rust. CONFIG.md `packages` section rewritten to document the per-language abstract-type conventions and the JavaScript caveat.

### Upgrade notes

- If you run slop on a codebase containing Java, C#, TypeScript, JavaScript, or Rust, the `packages` rule will now produce output where it previously returned nothing. `packages` is `severity = "warning"` by default, so this does not convert passing builds to failing builds without a config change. If the new coverage is noisy on your JS-only project (see caveat above), the quickest silencer is `[rules.packages]\nenabled = false` in your `.slop.toml`.
- `pyproject.toml` without a `[tool.slop]` section no longer halts slop's upward config walk (this landed in 0.5.0; called out here again because the implication for nested-project layouts is subtle). If a subproject pyproject was intentionally shielding a monorepo `.slop.toml`, add an explicit `[tool.slop]` table to keep that behavior.

## [0.5.0] - 2026-04-17

**Released to PyPI** on 2026-04-17 as `agent-slop-lint==0.5.0`. Tag: [`v0.5.0`](https://github.com/JordanGunn/agent-slop-lint/releases/tag/v0.5.0).

### Added

- **Two new complexity metrics exposed as rules**, both from well-cited prior art:
  - `halstead.volume` (V > 1500) and `halstead.difficulty` (D > 30), from Halstead's (1977) Software Science. Volume catches functions with high information content; Difficulty catches functions with dense operator/operand reuse. These cover the "moderate CCX but many distinct symbols" case that McCabe's cyclomatic complexity misses.
  - `npath` (NPath > 400), from Nejmeh (1988). Counts acyclic execution paths. Unlike CCX (additive), NPath is multiplicative, so ten sequential independent `if` statements produce CCX=11 but NPath=1024. This is the specific pattern agents produce when they dispatch on multiple flags.
- `CHANGELOG.md` (this file) documenting release history going forward. Historical entries for 0.1.0 through 0.4.0 are summaries, not exhaustive.
- CONFIG.md now has a "Note on default thresholds" section at the top documenting every default that diverges from its cited source, with rationale.

### Changed

- **slop is now self-contained.** The metric kernels previously imported from `aux-skills` on PyPI are vendored under `src/cli/slop/_aux/` (Apache-2.0 attributed in `NOTICE` and `src/cli/slop/_aux/LICENSE`). The `aux-skills` runtime dependency is removed; `pip install agent-slop-lint` now installs a single package. aux-skills was pre-1.0 and every kernel slop depended on had been modified in the last 90 days, so the external pin was absorbing breaking-change risk on a cadence slop did not control.
- **Repo layout.** The Python project is now under `src/` (with `src/pyproject.toml`, `src/cli/slop/` for the package, and `src/tests/` for tests). The repo top-level now contains only docs, scripts, skills, LICENSE, NOTICE, README, CHANGELOG, `.slop.toml`, and `.github/`. Dev workflow requires `cd src` before `uv sync` / `uv run pytest` / `uv build`. CI workflows set `working-directory: src` on the relevant steps.
- **Three default thresholds tuned** for contemporary and agentic practice. See CONFIG.md "Note on default thresholds" for per-rule rationale:
  - `complexity.weighted`: WMC > 50 → **WMC > 40** (tighter; closer to Fowler/Martin era advice, catches god-class drift earlier).
  - `halstead.volume`: V > 1000 → **V > 1500** (looser; 1000 flags legitimate orchestration functions, 1500 still flags the pathological three-responsibilities-fused case).
  - `npath`: NPath > 200 → **NPath > 400** (looser; Nejmeh's 1988 ceiling predates modern CLI dispatch — honest `click`/`argparse` main functions sit at NPath 256-512 without being rot).
- **Profiles also re-calibrated** to maintain their semantic relationship to the new defaults:
  - `lax`: WMC 100 → 80, Volume 1500 → 3000, NPath 500 → 1000.
  - `strict`: unchanged (already stricter than the new defaults).
- **Config discovery tweaked.** `_discover_config` now walks past a `pyproject.toml` that has no `[tool.slop]` table rather than stopping there. This lets sub-project pyproject files (like the new `src/pyproject.toml` in this repo) coexist with a repo-root `.slop.toml` in monorepos and nested layouts. Matches how ruff and mypy behave in practice.

### Removed

- `aux-skills` runtime dependency (vendored in; see above).
- `tool.uv.sources` override pointing at a sibling `../aux/cli` path. Development no longer depends on a locally-cloned aux repo.

### Upgrade notes

- Existing `.slop.toml` configs keep working. If you relied on explicit `weighted_threshold`, `volume_threshold`, or `npath_threshold` values, they take precedence over the new defaults.
- If you did NOT set those three thresholds explicitly and your codebase sits in the changed ranges, expect a different violation count on first run after upgrading. WMC went tighter (more violations likely); Volume and NPath went looser (fewer violations likely).
- Users in monorepos with `pyproject.toml` at a sub-project level AND a repo-root `.slop.toml`: discovery will now correctly find the root config instead of halting at the sub-project pyproject. If this changes the behavior you rely on, add an explicit `[tool.slop]` table to the sub-project pyproject.
- The `README.md` and `LICENSE` are tracked both at repo root (for GitHub) and inside `src/` (for PyPI, a hatchling constraint). Keep them in sync when editing.

## [0.4.0] - 2026-04-16

**Released to PyPI** on 2026-04-16 as `agent-slop-lint==0.4.0`. Tag: [`v0.4.0`](https://github.com/JordanGunn/agent-slop-lint/releases/tag/v0.4.0).

### Added

- `slop doctor` subcommand. Reports availability of `fd`, `rg`, and `git` so users can diagnose missing system dependencies before touching configuration.
- Preflight system-binary check runs automatically before `slop lint` and `slop check`. Missing required binaries produce an explicit error block and exit code 2 rather than silently returning zero files analyzed. Fixes a failure mode where `slop lint` on a machine without `fd` (notably some macOS setups) reported `✓ clean` with no violations.
- Upward config discovery. `slop lint` walks from the current directory toward the filesystem root looking for `.slop.toml` or `pyproject.toml` with `[tool.slop]`, matching ruff/mypy convention. `root` keys in a discovered config now resolve relative to the config file's directory, not CWD.
- Per-rule errors surfaced in human output (previously only JSON). Categories whose rules produced errors now show the error line and the status footer reads `ERROR`.

### Changed

- "Zero files analyzed" now renders as `⚠ no files matched` (yellow warning) rather than `✓ clean`, so genuinely empty scans cannot be mistaken for passing scans.
- A rule that produced errors and no violations is now coerced from `pass` to `error` in the engine layer, so silent failures cannot render as clean.
- `format_human` refactored from a monolith to named helpers with a `_CategoryAgg` dataclass. Dogfood complexity now within slop's own thresholds.

## [0.3.1] - 2026-04-13

**Released to PyPI** on 2026-04-13 as `agent-slop-lint==0.3.1`. Tag: [`v0.3.1`](https://github.com/JordanGunn/agent-slop-lint/releases/tag/v0.3.1).

### Added

- `slop hook` subcommand to install or remove a git pre-commit hook that runs `slop lint --output quiet`.

## [0.3.0] - 2026-04-13

**Released to PyPI** on 2026-04-13 as `agent-slop-lint==0.3.0`. Tag: [`v0.3.0`](https://github.com/JordanGunn/agent-slop-lint/releases/tag/v0.3.0).

### Added

- `slop skill <dir>` subcommand to copy the bundled agent skill into any directory (for Claude Code / Cursor / other agents).
- `slop init [default|lax|strict]` profile selection.
- `docs/CONFIG.md` rule-by-rule configuration reference.
- `docs/SETUP.md` install-configure-integrate-verify guide.
- `llms.txt` for agent-friendly project discovery.

## [0.2.0] - 2026-04-12

**Released to PyPI** on 2026-04-12 as `agent-slop-lint==0.2.0`. Tag: [`v0.2.0`](https://github.com/JordanGunn/agent-slop-lint/releases/tag/v0.2.0).

### Changed

- Hotspot metric moved to LOC-delta churn proxy (was commit count) and defaults tightened to a 14-day window (was 90d), calibrated for agentic code generation timescales.
- `aux-skills` pulled from PyPI rather than a sibling git path (internal-dev convenience).

## [0.1.0] - 2026-04-10

**Released to PyPI** on 2026-04-11 as `agent-slop-lint==0.1.0`. Tag: [`v0.1.0`](https://github.com/JordanGunn/agent-slop-lint/releases/tag/v0.1.0).

### Added

- Initial release. Ten rules across six categories: `complexity.cyclomatic`, `complexity.cognitive`, `complexity.weighted`, `hotspots`, `packages`, `deps`, `orphans`, `class.coupling`, `class.inheritance.depth`, `class.inheritance.children`.
- Backed by `aux-skills` kernels (tree-sitter, ripgrep, fd, git).
- `slop lint`, `slop check`, `slop rules`, `slop init`, `slop schema` subcommands.
- Human, JSON, and quiet output formats.
- `.slop.toml` and `pyproject.toml [tool.slop]` config support.
- PyPI distribution as `agent-slop-lint`.

[Unreleased]: https://github.com/JordanGunn/agent-slop-lint/compare/v0.6.1...HEAD
[0.6.1]: https://github.com/JordanGunn/agent-slop-lint/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/JordanGunn/agent-slop-lint/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/JordanGunn/agent-slop-lint/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/JordanGunn/agent-slop-lint/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/JordanGunn/agent-slop-lint/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/JordanGunn/agent-slop-lint/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/JordanGunn/agent-slop-lint/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/JordanGunn/agent-slop-lint/releases/tag/v0.1.0
