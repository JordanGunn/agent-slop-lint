"""Signal computation for first-parameter clusters.

These helpers compute the multi-signal profile (body-shape Jaccard,
receiver-call density, modal-token overlap) that classifies a
``FirstParameterCluster`` as ``missing_class`` / ``strategy_family``
/ ``heterogeneous`` / ``infrastructure`` / ``false_positive``.

Used internally by ``Lexicon.first_param_clusters`` to enrich the
clusters it returns. Rules read the populated fields off the
cluster; they do not call these helpers directly.

PoC references: ``scripts/research/composition_poc_v2/poc{2,6}_*.py``.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from slop.lexicon.affix import UNIVERSAL_NOISE


_LEAF_OR_NOISE = frozenset({
    "identifier", "integer", "float", "string", "string_content",
    "true", "false", "none", "comment",
    ":", ",", "(", ")", "[", "]", "{", "}", ".",
    "=", "+", "-", "*", "/", "%", "<", ">", "==", "!=",
    "string_start", "string_end",
})


_FALSE_POSITIVE_NAMES: frozenset[str] = frozenset({
    "node", "tree",          # tree-sitter library types
})
_INFRASTRUCTURE_NAMES: frozenset[str] = frozenset({
    "root", "file_path", "path", "fp",
})


def classify_cluster(
    parameter_name: str,
    parameter_types: set[str],  # noqa: ARG001 — accepted for symmetry; reserved
    exempt_names: frozenset[str],
) -> tuple[str, str]:
    """Return ``(verdict, advisory)`` for a first-parameter cluster.

    Verdict precedes profile: ``false_positive`` and ``weak`` short-
    circuit the multi-signal classification.
    """
    if parameter_name in _FALSE_POSITIVE_NAMES or parameter_name in exempt_names:
        return ("false_positive",
                f"`{parameter_name}` is typically a third-party library "
                f"type or otherwise marked exempt; wrapping it in a slop "
                f"class would create an adapter layer with no clear "
                f"benefit.")
    if parameter_name in _INFRASTRUCTURE_NAMES:
        return ("weak",
                f"`{parameter_name}` is an infrastructure parameter "
                f"(filesystem path / scan root). The cluster reflects "
                f"shared configuration plumbing, not a missing class.")
    return ("strong",
            f"`{parameter_name}` is the natural receiver of these "
            f"methods. Folding them into a class with `{parameter_name}` "
            f"as ``self`` is the textbook conversion.")


def _signature_ngrams(node, n: int = 3) -> set[tuple[str, ...]]:
    """AST node-type ``n``-grams over a function body (PoC v2.2)."""
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
    """Count ``param.attr`` + ``param[k]`` references in body (PoC v2.6).

    Proxies "is this parameter being treated as a receiver?".
    """
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


def _modal_tokens(
    member_names: list[str],
    *,
    k: int = 3,
    exclude: frozenset[str] = UNIVERSAL_NOISE,
) -> set[str]:
    """Top-``k`` tokens across the member names after filtering."""
    from slop.lexicon._tokens import split_tokens
    c: Counter[str] = Counter()
    for name in member_names:
        for t in split_tokens(name):
            tl = t.lower()
            if tl not in exclude:
                c[tl] += 1
    return {t for t, _ in c.most_common(k)}


def _overlap(name: str, modal: set[str], exclude: frozenset[str]) -> float:
    from slop.lexicon._tokens import split_tokens
    my = {t.lower() for t in split_tokens(name) if t.lower() not in exclude}
    if not my:
        return 0.0
    return len(my & modal) / len(my)


def profile_cluster(
    cluster: Any,
    bodies: dict[tuple[str, str], tuple[Any, bytes]],
) -> None:
    """Compute body-shape Jaccard mean, receiver-call density, and
    modal-token overlap for a cluster; mutate the cluster in place
    with the signal values + a ``profile_label``."""
    members_with_body = [
        (name, file, line) for name, file, line in cluster.members
        if (file, name) in bodies
    ]
    if len(members_with_body) < 2:
        return

    sigs: list[tuple[set[tuple[str, ...]], int]] = []
    member_names: list[str] = []
    for name, file, _line in members_with_body:
        body_node, content = bodies[(file, name)]
        sigs.append((
            _signature_ngrams(body_node),
            _receiver_call_count(body_node, content, cluster.parameter_name),
        ))
        member_names.append(name)

    # Body-shape Jaccard mean across all member pairs.
    pair_scores: list[float] = []
    for i in range(len(sigs)):
        for j in range(i + 1, len(sigs)):
            pair_scores.append(_jaccard(sigs[i][0], sigs[j][0]))
    cluster.body_jaccard_mean = (
        sum(pair_scores) / len(pair_scores) if pair_scores else 0.0
    )

    # Receiver-call density mean.
    cluster.mean_receiver_calls = (
        sum(rc for _, rc in sigs) / len(sigs) if sigs else 0.0
    )

    # Modal-token overlap mean. UNIVERSAL_NOISE strips Newman 14 +
    # English glue before computing modal tokens — without it generic
    # words like "id", "result", "next" dominate and inflate overlap.
    modal = _modal_tokens(member_names)
    if modal:
        per_member_overlap = [
            _overlap(name, modal, UNIVERSAL_NOISE)
            for name in member_names
        ]
        per_member_overlap = [v for v in per_member_overlap if v or v == 0.0]
        if per_member_overlap:
            cluster.modal_overlap_mean = (
                sum(per_member_overlap) / len(per_member_overlap)
            )

    # Profile label: combine signals into a single advisory class.
    if cluster.verdict == "false_positive":
        cluster.profile_label = "false_positive"
    elif cluster.verdict == "weak":
        cluster.profile_label = "infrastructure"
    elif cluster.body_jaccard_mean >= 0.7 and cluster.mean_receiver_calls < 0.5:
        cluster.profile_label = "strategy_family"
    elif cluster.mean_receiver_calls >= 1.0:
        cluster.profile_label = "missing_class"
    else:
        cluster.profile_label = "heterogeneous"
