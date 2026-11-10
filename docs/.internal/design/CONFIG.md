## Config Model

Config exposes **verdict thresholds, not primitives** — the same way the linter surfaces
Martin's distance-from-main-sequence (one threshold) and never Ca/Ce/Na/Nc.

- A **primitive** (hapax ratio, token count) always lives on the view and is *never* a
  config knob.
- A **verdict metric** is a named composite with an equation; only its threshold is
  config-surfaced.
- **Algorithm internals** (clustering cutoffs) are module constants, not config.
- **Noise floors** (min cluster size, min distinct tokens) are significance gates,
  legitimately config-surfaced even for observations — they govern output volume,
  not the claim.

Thresholds are keyed by **altitude**, validated at config-load against each rule's
declared altitudes — a threshold key the rule does not declare is a load error, not
a silent drop.

**Lexical migration.** Unproven lexical signals ship as **observations with no
verdict threshold**. When a signal proves consistent across corpora it is promoted:
named, given an equation, and given a single config threshold — an **additive**
schema change (old configs still validate), never a subtractive one. This is *why*
primitive knobs must not enter the schema now: removing them later would be breaking.
Triage, not uniform promotion — some signals stay observations forever
(vocabulary/Zipf, dispersion), some are cut as pure style.