"""PoC v2.6 — Multi-criteria ranking of cluster members.

For each first-parameter cluster, compute multiple quality signals
per member and combine them into a ranked candidate list. The
member that scores highest on multiple criteria is the strongest
"belongs in the candidate class" candidate.

Criteria
--------
1. **Body-shape similarity to cluster median** — does this member's
   body look like the rest of the cluster's? (Type-2 clone signal,
   per PoC v2.2.)
2. **Receiver-call density on first param** — does this member
   actually CALL methods on its first parameter, or just use it as
   a value? Heavy receiver-call use is the textbook "this is a
   method" signal.
3. **Token overlap with cluster modal text** — does this member's
   name share dominant tokens with siblings? (Per PoC v2.1.)

Aggregate score = weighted sum. High score on all three = strong
candidate; high body-similarity but low receiver-call = strategy
function not method.

Theoretical grounding
---------------------
- Tsantalis & Chatzigeorgiou (2009) "Identification of Move Method
  Refactoring Opportunities" — multi-criteria ranking of refactoring
  candidates. (Citation hedge: I'm confident the paper exists and
  uses multi-criteria scoring; I want to verify whether the method
  is specifically named MOORA before citing it as such in slop's
  docs.)
- The general "multi-objective scoring of refactoring opportunities"
  line of research, also: Bavota et al. (2010), Fokaefs et al.
  (2009) JDeodorant.

Usage
-----
    cd src
    uv run python ../scripts/research/composition_poc_v2/poc6_multi_criteria_rank.py cli/slop
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from slop._lexical._naming import enumerate_functions
from slop._lexical.identifier_tokens import split_identifier
from slop._structural.composition import first_parameter_drift_kernel


_LEAF_OR_NOISE = frozenset({
    "identifier", "integer", "float", "string", "string_content",
    "true", "false", "none", "comment",
    ":", ",", "(", ")", "[", "]", "{", "}", ".",
    "=", "+", "-", "*", "/", "%", "<", ">", "==", "!=",
    "string_start", "string_end",
})


def _signature_ngrams(node, n: int = 3) -> set[tuple[str, ...]]:
    seq: list[str] = []

    def walk(nn):
        if nn.type not in _LEAF_OR_NOISE:
            seq.append(nn.type)
        for child in nn.children:
            walk(child)
    walk(node)
    if len(seq) < n:
        return {tuple(seq)} if seq else set()
    return {tuple(seq[i:i + n]) for i in range(len(seq) - n + 1)}


def _receiver_call_count(body, content: bytes, param_name: str) -> int:
    """Count attribute / call accesses on the first param: ``param.x``,
    ``param.method()``, ``param[k]``."""
    count = 0

    def walk(node):
        nonlocal count
        if node.type == "attribute":
            obj = node.child_by_field_name("object")
            if obj is not None and obj.type == "identifier":
                text = content[obj.start_byte:obj.end_byte].decode(
                    "utf-8", errors="replace",
                )
                if text == param_name:
                    count += 1
        if node.type == "subscript":
            value = node.child_by_field_name("value")
            if value is not None and value.type == "identifier":
                text = content[value.start_byte:value.end_byte].decode(
                    "utf-8", errors="replace",
                )
                if text == param_name:
                    count += 1
        for child in node.children:
            walk(child)
    walk(body)
    return count


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main(root: str) -> None:
    print("# PoC v2.6 — Multi-criteria ranking of cluster members")
    print()
    rp = Path(root)
    drift_result = first_parameter_drift_kernel(rp, languages=["python"])

    # Index function bodies and contexts
    contexts: dict[tuple[str, str], dict] = {}
    for ctx in enumerate_functions(rp, languages=["python"]):
        if ctx.body_node is None:
            continue
        contexts[(ctx.file, ctx.name)] = {
            "body_node": ctx.body_node,
            "content": ctx.content,
        }

    print(f"Root: `{root}`  |  Clusters: {len(drift_result.clusters)}")
    print()

    for c in drift_result.clusters:
        if c.verdict != "strong":
            continue
        members = [
            (n, f, l) for n, f, l in c.members
            if (f, n) in contexts
        ]
        if len(members) < 2:
            continue

        # Compute body-shape ngrams per member
        sigs: list[tuple[str, str, set[tuple[str, ...]], int]] = []
        # Cluster modal token bag
        all_name_tokens: list[str] = []
        for name, file, _ in members:
            ctx_data = contexts[(file, name)]
            ng = _signature_ngrams(ctx_data["body_node"])
            rc = _receiver_call_count(
                ctx_data["body_node"], ctx_data["content"], c.parameter_name,
            )
            sigs.append((name, file, ng, rc))
            all_name_tokens.extend(
                t.lower() for t in split_identifier(name)
            )
        modal_tokens = {t for t, _ in Counter(all_name_tokens).most_common(3)}

        # Score each member
        print(f"### `{c.parameter_name}` in `{c.scope}` ({len(members)} members)")
        print()
        print("| Member | Body-similarity | Receiver-call density | Modal-token overlap | Score |")
        print("|---|---|---|---|---|")
        scored: list[tuple] = []
        for i, (name, file, ng, rc) in enumerate(sigs):
            other_ngs = [s[2] for j, s in enumerate(sigs) if i != j]
            mean_sim = (
                sum(_jaccard(ng, o) for o in other_ngs) / len(other_ngs)
                if other_ngs else 0.0
            )
            # Receiver density: receiver-calls per 100 ngrams of body
            rc_density = rc / max(1, len(ng) / 100)
            # Modal overlap: fraction of this name's tokens in modal set
            my_tokens = {t.lower() for t in split_identifier(name)}
            modal_overlap = (
                len(my_tokens & modal_tokens) / len(my_tokens)
                if my_tokens else 0.0
            )
            score = mean_sim * 0.4 + min(rc_density / 10, 1.0) * 0.4 + modal_overlap * 0.2
            scored.append((score, name, file, mean_sim, rc, modal_overlap))

        scored.sort(reverse=True)
        for score, name, file, sim, rc, overlap in scored:
            print(
                f"| `{name}` ({file}) | {sim:.2f} | {rc} calls | "
                f"{overlap:.2f} | **{score:.2f}** |"
            )
        print()
        # Verdict reading
        top = scored[0] if scored else None
        bottom = scored[-1] if scored else None
        if top and bottom and (top[0] - bottom[0]) > 0.3:
            print("_Verdict: heterogeneous cluster — top and bottom members differ significantly. "
                  "Consider whether the bottom members belong elsewhere._")
        elif top and top[3] >= 0.5 and top[4] >= 3:
            print("_Verdict: cohesive cluster with active receiver-call use — strong "
                  "candidate for class extraction._")
        else:
            print("_Verdict: cluster shares input but limited receiver-call evidence — "
                  "likely strategy/transform family rather than missing class._")
        print()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
