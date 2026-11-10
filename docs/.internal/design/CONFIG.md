## Config Model

Config exposes **thresholds on named measures, not primitives**: Martin's
distance-from-main-sequence has one threshold, never Ca/Ce/Na/Nc.

- A **primitive** (hapax ratio, token count) lives on the view and is *never* a config knob.
- A **measure** is a named composite with an equation; only its threshold is
  config-surfaced.
- **Algorithm internals** (clustering cutoffs) are module constants, not config.
- **Noise floors** (e.g. `structure.duplication`'s `params.min_leaf_nodes`) are significance
  gates, legitimately config-surfaced: they govern output volume, not the limit.

Thresholds are keyed by **altitude**, validated at config-load against each rule's
declared altitudes: a threshold key the rule does not declare is a load error, not
a silent drop. A config file may contain only `exclude`, `languages` and `rules`; any
other top-level key is a load error. A rule table accepts `enabled`, `thresholds` and
`params` only.

Exemptions are inline (`slop: ignore[rule]` on the reported line), not config.

New knobs are an **additive** schema change (old configs still validate); removing one is
breaking, which is why primitive knobs must not enter the schema.
