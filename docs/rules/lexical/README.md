# Lexical rules

Lexical rules measure vocabulary discipline. Their substrate is
identifier strings and AST scope names. Each rule points at a
specific architectural smell that's visible at the lexical
level: missing namespace, missing receiver, naming inconsistency,
dispatch-encoded-in-names, file holding multiple cohesive units.

The rules collectively form slop's catalog of agentic naming
failures — patterns that accumulate when no one is enforcing
naming discipline across additions to a codebase. See
[`docs/philosophy/naming-spec.md`](../../philosophy/naming-spec.md)
for the principles every rule name conforms to, and
[`docs/observations/composition/03.md`](../../observations/composition/03.md)
for the empirical work that drove the v1.2.0 rule layout.

## Rule index

| Rule | Default | What it catches |
|---|---|---|
| [`lexical.stutter`](stutter.md) | ≥ 2 tokens | Names repeating tokens from any enclosing scope (package/module/class/function) |
| [`lexical.verbosity`](verbosity.md) | > 3 tokens | Function/class names with too many word-tokens — missing namespace |
| [`lexical.cowards`](cowards.md) | any match | Identifiers ending in disambiguator suffixes (`_v1`, `_v2`, `_old`, `_new`, `_local`) — provenance collapse |
| [`lexical.hammers`](hammers.md) | banlist match | Catchall vocabulary (`Manager`, `Helper`, `Util`, `Spec`, `Object`) — one word for every nail |
| [`lexical.tautology`](tautology.md) | suffix matches type | Identifier suffixes that tautologically restate type annotations (`_dict`, `_path`, `_str`) |
| [`lexical.sprawl`](sprawl.md) | ≥ 3 alphabet × ≥ 2 ops | Closed alphabet sprawls across naming templates (Wille 1982 FCA) |
| [`lexical.imposters`](imposters.md) | ≥ 3 fns sharing param | Parameters camouflaged as ordinary deps; missing receiver class |
| [`lexical.slackers`](slackers.md) | < 30% template coverage | Sibling functions sharing input but refusing to align by naming |
| [`lexical.confusion`](confusion.md) | ≥ 2 strong receivers in one file | File holds multiple distinct cohesive units (Lanza & Marinescu Extract Class) |

## Category properties

- **Substrate:** identifier strings and AST scope names. Tokens
  split on snake_case + CamelCase + acronym boundaries.
- **Compute profile:** moderate. Most rules walk the function
  index from `_lexical/_naming.py`; the multi-signal rules
  (imposters, slackers, confusion) additionally walk function
  bodies for AST n-grams + receiver-call counts.
- **Determinism:** full. Identical source produces identical
  output.
- **Failure modes:** test fixtures (pytest's `tmp_path`,
  per-language test families) routinely trigger imposters and
  sprawl; waivable via path-scoped waivers in `.slop.toml`.
- **Interpretation burden:** moderate. Findings often need a
  human to disambiguate "real architectural debt" from "framework
  convention" (see waivers section below).

## Why these rules

Slop's thesis: lexical messiness is the visible artifact of
unenforced naming discipline. Each rule targets a specific
manifestation:

| Rule | Architectural debt it points at |
|---|---|
| `stutter` | Names compensating for scope (could exist higher up the hierarchy) |
| `verbosity` | Function/class is a class-without-class (extract namespace/class) |
| `cowards` | Codebase couldn't commit to one implementation (rename to describe what differs) |
| `hammers` | No real noun was available; placeholder hammered into shape |
| `tautology` | Suffix duplicating the type system; redundant with annotation |
| `sprawl` | Closed alphabet acting as undeclared type (declare it) |
| `imposters` | Receiver-shaped parameter without a class (extract class) |
| `slackers` | Real cluster with no naming convention (rename for consistency) |
| `confusion` | File doing the work of multiple cohesive units (split file) |

## v1.2.0 changes

The v1.1.x state had 11 lexical rules + 2 composition rules
(13 total). v1.2.0 cuts six and renames four:

- **Cut:** `verbosity` (body mean), `tersity`, `boilerplate_docstrings`,
  `identifier_singletons` — style measurements that don't validate
  the structural-debt thesis. Plus `composition.affix_polymorphism`,
  `composition.first_parameter_drift` (renamed, suite collapsed).
  Plus the v1.1.0 stutter sub-rule split.
- **Renamed:** `name_verbosity` → `verbosity`,
  `numbered_variants` → `cowards`, `weasel_words` → `hammers`,
  `type_tag_suffixes` → `tautology`, plus the two composition
  rules.
- **Suite collapsed:** `composition.*` ceases to exist. All
  detection moves into `lexical.*` per slop's substrate-naming
  convention.

Total: 9 lexical rules, all spec-conformant per
[`docs/philosophy/naming-spec.md`](../../philosophy/naming-spec.md).

## Waivers

Lexical rules can produce noise on framework conventions and
test code. Common waivers:

- `lexical.imposters` and `lexical.slackers` on `tests/**` —
  pytest functions clustering on `tmp_path` are fixtures, not
  hidden classes
- `lexical.tautology` on `tests/**` — `tmp_path: Path` is a
  pytest convention, not a tautology to fix
- `lexical.sprawl` on `tests/**` — per-language test files
  legitimately share parallel function names
- `lexical.cowards` on `tests/**` — test names ending in
  `_old`/`_new` describe what's being tested, not arbitrary
  disambiguators
- `lexical.hammers` on `tests/**` — test names referencing
  rule severities (`_info`, `_warning`) describe the test, not
  catchall vocabulary
- `lexical.verbosity` (project-wide on agent-written codebases) —
  high volume is the signal, not noise; track it via the count
  while waiving individual hits

See the dogfood `.slop.toml` for canonical waiver shapes.
