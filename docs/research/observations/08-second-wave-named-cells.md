# Observation 08 — Second-wave validation: named cells of the overlap matrix

**Date:** 2026-05-17
**Primitives landed:** `Lexicon.middle_spread(min_spread, max_frequency)`, `Lexicon.packet_isolates(min_bags, min_association, min_frequency)`. Second wave per A12, unblocked by obs 07's overlap-matrix evidence.
**Corpora:** v1.2.0 snapshot and current dev.
**Thresholds (recorded inline):** `middle_spread(min_spread=4)`, `packet_isolates(min_bags=5, min_association=0.7, min_frequency=8)`, `UNIVERSAL_NOISE` stripped.

## Why these methods, why now

Obs 07's overlap matrix showed that two cells of the 2×2×2 cube are large and informative enough to deserve direct named primitives:

- **`(--C)` diffuse-domain cell** (snapshot: 6; dev: 15) — surfaced by `middle_spread`. Spread without frequency-head dominance; often the most actionable refactor candidates.
- **`(-BC)` hub cell** (snapshot: 48; dev: 55) — surfaced by `packet_isolates`. Frequency-head presence + spread, but failure to form a packet. The empirical hub signature.

Per A12 the second-wave methods were gated on obs 07's evidence of non-redundancy. The matrix occupancy made the case: callers were already computing these cells manually by subtracting plane-membership sets. Named primitives remove the subtraction step.

## Results

### `middle_spread` — diffuse-domain candidates

**Snapshot (28 tokens; top 12 by spread):**
```
results              freq= 11  spread=10
entry                freq= 10  spread=10
check                freq= 11  spread= 9
call                 freq=  9  spread= 8
identifier           freq= 10  spread= 7
parse                freq=  9  spread= 7
types                freq= 10  spread= 6
density              freq=  9  spread= 6
default              freq= 10  spread= 5
names                freq=  9  spread= 5
metrics              freq=  8  spread= 5
resolve              freq=  8  spread= 5
```

**Dev (56 tokens; top 12 by spread):**
```
escape               freq= 11  spread=11
abstract             freq= 10  spread=10
catch                freq= 10  spread=10
hatch                freq= 10  spread=10
mutators             freq= 10  spread=10
parser               freq= 10  spread=10
try                  freq= 10  spread=10
add                  freq=  9  spread= 9
cmd                  freq=  9  spread= 9
superclasses         freq=  9  spread= 9
compute              freq= 11  spread= 8
methods              freq=  9  spread= 8
```

### `packet_isolates` (min_freq=8, head only) — empirical hub diagnostic

**Snapshot (70 tokens; top 12 by freq):**
```
node       144   config     110   root       110
content     94   name        73   rule        61
file        53   language    37   function    36
path        36   min         32   max         30
```

**Dev (63 tokens; top 12 by freq):**
```
nodes      150   node       105   content     70
config      62   parses      48   methods     41
qualname    41   slop        39   file        38
parts       37   types       37   ...
```

## Interpretation

### `middle_spread` surfaces two distinct patterns

**Snapshot's `middle_spread` is dominated by domain vocabulary**: `results`, `entry`, `check`, `identifier`, `parse`, `metrics`, `resolve`. These are not infrastructure — they name *operations the codebase performs*. Several look like missing-module candidates: `parse` (7 files) and `identifier` (7 files) both suggest a missing `parsing/` or `identifiers/` module.

**Dev's `middle_spread` is dominated by ABC-method-name tokens**: `escape`/`hatch` (escape_hatch), `abstract`, `catch`, `try`, `mutators` (hidden_mutators), `add`/`cmd`/`parser` (CLI subcommand convention), `superclasses` (`Language.superclasses`). These are conventional packets per obs 04 — *vocabulary owned by a defining class but seen across many files that implement the interface*. The class-ownership filter from obs 04 would absorb most of these.

**Friction worth recording**: `middle_spread` doesn't apply the class-ownership filter. A token can be in the conventional-packet zone (covered by an ABC vocabulary) and still appear here because the cell-membership test is set-based, not class-coverage-based. The two filters compose but don't subsume each other. For corrective-action mapping (D2), the right pipeline is: `middle_spread` → `split_packets_by_class_ownership` → action mapping.

### `packet_isolates` is a clean hub diagnostic

The top tokens in *both* corpora are unambiguous infrastructure:

- **Cross-corpus persistent hubs**: `node`, `content`, `root`, `config`, `name`, `file`, `language`, `min`, `max`, `path`. These are the threaded-everywhere values — `Path` objects, AST nodes, byte content, name strings.
- **Dev introduces `nodes`, `parses`, `qualname`, `parts`, `methods`** — new infrastructure tokens that emerged from the substrate refactor (the parsed `ParseResult` carries `callable_nodes`, `qualname` is the standard scope key, etc.).

These are correctly *not* refactor targets. The diagnostic value is the explicit list: when grading the output of `lexical.sprawl` against a corpus, the `packet_isolates` set tells you "these tokens are hubs, don't recommend extracting them."

## What this changes about the corrective-action pipeline

Today's `slop.lexicon.actions.map_packets_to_actions` operates on packet shape only. With the named-cell primitives, the natural extension is **cell-aware advisory generation**:

```
(ABC) packet                → extract_dataclass / extract_class (high confidence)
(AB-) packet (local)        → name_pattern / local convention
(A-C) packet (cross-file)   → extract_module / cross-cutting concern
(A--) packet (small/local)  → named_tuple / small refactor (low priority)
(-BC) isolate (hub)         → no action; informational ("don't extract this")
(--C) middle_spread         → review for missing-module candidates
(-B-) concentrated freq     → review for over-vocabularised local code
```

This is a richer surface than packet-shape-alone could produce. The seven non-trivial cells correspond to seven distinct corrective-action contexts. Documenting now; implementing in a future observation that joins the cell labels to the action-mapping output.

## Cross-corpus reading

Comparing snapshot's `middle_spread` vs. dev's:

- Snapshot's top entries (`results`, `entry`, `check`, `identifier`, `parse`) are mostly *domain vocabulary that hasn't been organised*. Genuine refactor targets.
- Dev's top entries are mostly *ABC-method tokens* (`escape`, `hatch`, `abstract`, `catch`, `try`, `mutators`, `superclasses`) or *CLI convention tokens* (`add`, `cmd`, `parser`). These are NOT refactor targets — the architecture already owns them.

Dev's `middle_spread` cell is *bigger* (56 vs. 28) but *less actionable in raw form*. After the class-ownership filter is applied, the actionable subset will shrink dramatically. This is exactly the kind of compositional analysis obs 07 predicted would matter.

## What this completes (per the active /goal contract)

- ✓ First-wave methods (`hapax_ratio`, `spread_dominant`, `frequency_head`) landed with tests; obs 07 records.
- ✓ Second-wave methods (`middle_spread`, `packet_isolates`) landed with tests, gated on obs 07 evidence (this observation records).
- ✓ Each method exercised against snapshot (primary) + dev tree.
- ✓ Conventional vs pathological distinction maintained.
- ✓ Thresholds recorded inline.
- ✓ Obs 07 answered: the three planes diverge empirically; intersection cells are load-bearing.
- ✓ Second-wave decision followed obs 07 data (both methods justified).

## What's next

The cell-aware advisory mapping sketched above is the natural next observation. Specifically: take dev's `middle_spread` output, apply `split_packets_by_class_ownership`, and tabulate how many of the 56 entries survive as genuinely pathological vs. how many are absorbed as conventional. Predicted: > 50% absorbed. If true, the corrective-action map should weight cell-membership × class-ownership as a composite signal rather than relying on cell-membership alone.
