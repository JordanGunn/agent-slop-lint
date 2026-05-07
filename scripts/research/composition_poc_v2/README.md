# Composition PoC v2 — concept-shape recognition

The original PoCs (`scripts/research/composition_poc/poc{1..5}.py`)
established that detection works: token-edit-distance + FCA reliably
finds closed-alphabet patterns and missing-namespace candidates. The
v1.1.0 dogfood (recorded in
[`docs/observations/dogfood/01.md`](../../../docs/observations/dogfood/01.md))
revealed a follow-on problem: the rule's advisory ("fold into a class
with `X` as `self`") doesn't match what the cluster actually IS in
many cases. Slop's own `color.py` `red/green/yellow/bold/dim`
cluster is correctly detected, but it's idiomatic free-function
strategy code, not a missing class.

These PoCs experiment with methods to **describe what a cluster
actually is** — using dominant text and core AST shapes empirically,
without imposing pattern-language vocabulary like
"strategy/receiver/pipeline." The goal is signal palpable enough
that an agent reading the output recognizes the right composition
move (or recognizes that no move is warranted) without the rule
having to assert one.

## Methods

| PoC | Method | Grounding |
|---|---|---|
| `poc1_dominant_text.py` | Bag-of-tokens + modal-token labeling per cluster | Caprile & Tonella 2000 (loose); standard TF |
| `poc2_body_shape.py` | AST-node-type signature similarity within cluster | Type-2 clone detection (Roy 2009; Baxter 1998) |
| `poc3_alphabet_entity.py` | Score closed alphabets by spread across stems / files / module dicts | Novel — extends Wille FCA |
| `poc4_within_cluster_affix.py` | Apply existing affix detection to cluster member names | Caprile & Tonella; Wille FCA at finer scope |
| `poc5_rtm_topics.py` | LDA over function-body identifier tokens | Bavota et al. 2014 *Methodbook* (RTM) |
| `poc6_multi_criteria_rank.py` | Combine body-shape similarity + first-param attribute access | Tsantalis & Chatzigeorgiou 2009 (style) |
| `poc7_lanza_marinescu.py` | Compose existing slop metrics into Extract Class detection rule | Lanza & Marinescu 2006 *Object-Oriented Metrics in Practice* |

## Running

```bash
cd /home/jgodau/work/personal/slop/src
uv run python ../scripts/research/composition_poc_v2/poc1_dominant_text.py cli/slop > ../scripts/research/composition_poc_v2/output_poc1.md
# ... and so on for each PoC

# v2.5 (RTM) requires sklearn:
uv pip install scikit-learn
```

## Observations

After all PoCs run, observations are recorded in
[`docs/observations/composition/03.md`](../../../docs/observations/composition/03.md)
— including which methods produce defensible, agent-actionable
output and which combination is worth promoting to a kernel.
