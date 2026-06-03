## Config Model

Config exposes **batteries, not primitives** — the same way the linter surfaces
Martin's distance-from-main-sequence (one threshold) and never Ca/Ce/Na/Nc.

- A **primitive** (hapax ratio, token count, FCA alphabet size) always lives on the
  view and is *never* a config knob.
- A **battery** is a named composite with an equation — the verdict-bearing metric.
  Only the battery threshold is config-surfaced.
- **Algorithm internals** (FCA extents, clustering cutoffs) are module constants,
  not config.
- **Noise floors** (min cluster size, min annotations) are significance gates,
  legitimately config-surfaced even for observations — they govern output volume,
  not the claim.

Thresholds are keyed by **altitude**, validated at config-load against each rule's
declared altitudes — a threshold key the rule does not declare is a load error, not
a silent drop.

**Lexical migration.** Unproven lexical signals ship as **observations with no
verdict threshold**. When a battery proves a consistent signal across corpora it is
promoted: named, given an equation, and given a single config threshold — an
**additive** schema change (old configs still validate), never a subtractive one.
This is *why* primitive knobs must not enter the schema now: removing them later
would be breaking. Triage, not uniform promotion — some signals promote (imposters:
receiver-density × cohesion; sprawl), some stay observations forever
(vocabulary/Zipf, dispersion), some are cut as pure style.
