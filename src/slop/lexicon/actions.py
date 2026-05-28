"""Corrective-action mapping — packet shape → suggested refactor.

Translates *pathological* packets (those that survived the class-ownership
filter in ``slop.lexicon.filters``) into named refactor advisories an
agent can act on. The taxonomy is derived from observation 02's
corrective-action table and refined by the discovery in observation 03
that token provenance (parameter vs entity-name) is the key
classification signal.

Categories:

- ``extract_dataclass`` — ≥3 tokens that all appear only as parameter
  names, recurring across many callables. The FindOptions case. High
  confidence advisory: bundle the parameters into a single dataclass.
- ``named_tuple`` — 2 tokens that always travel together as a parameter
  pair. A small recurring pair worth a named tuple or kwargs-only
  signature with documentation.
- ``extract_module`` — ≥3 tokens that all appear only as entity names
  (function / class), recurring across many files. The "pdf sprawled
  across many places" case from observation 01. Advisory: extract a
  module owning the shared concept.
- ``missing_class`` — mixed-provenance packet (some name tokens, some
  parameter tokens) at file scope. The vocabulary spans declarations
  and signatures; a class would unify them.
- ``naming_convention`` — mixed-provenance packet at callable scope.
  Likely a registry / wrapper convention (``run_X`` returning ``Slop``,
  ``add_parser(subparsers)``). Advisory: document the convention; an
  ABC or protocol may make it enforceable.
- ``review`` — packet too small or shape doesn't match any high-
  confidence category. Surface for human review without a strong
  prescription.

See ``docs/research/observations/02-cooccurrence-packets.md`` for the
initial taxonomy and ``docs/research/observations/04-class-ownership-filter.md``
for the conventional/pathological precondition.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from slop.lexicon.view import Lexicon


@dataclass(frozen=True)
class CorrectiveAction:
    """One packet → refactor advisory."""

    packet: frozenset[str]
    kind: str          # see module docstring for the closed set
    confidence: str    # "high" | "medium" | "low"
    advisory: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "packet": sorted(self.packet),
            "kind": self.kind,
            "confidence": self.confidence,
            "advisory": self.advisory,
            "evidence": self.evidence,
        }


def _token_provenance(
    lexicon: Lexicon,
    tokens: set[str],
) -> dict[str, dict[str, int]]:
    """Compute per-token provenance: how often each token appears as a
    parameter name vs an entity (function/class) name across the view.

    Returns ``{token: {"name": n_entity_uses, "param": n_param_uses}}``.
    """
    out: dict[str, dict[str, int]] = {t: {"name": 0, "param": 0} for t in tokens}
    for entity in lexicon.named_entities():
        for t in entity.tokens:
            tl = t.lower()
            if tl in out:
                out[tl]["name"] += 1
    for c in lexicon.callables():
        for p in c.parameters:
            if p.name in ("self", "cls"):
                continue
            for t in Lexicon.split_tokens(p.name):
                tl = t.lower()
                if tl in out:
                    out[tl]["param"] += 1
    return out


def _classify_provenance(token_prov: dict[str, dict[str, int]]) -> str:
    """Summarise the provenance map into one of:
    ``all_param`` | ``mostly_param`` | ``all_name`` | ``mostly_name``
    | ``mixed`` | ``none``.

    ``mostly_param`` / ``mostly_name`` are the per-token majority shapes:
    a token counts as "param-favoured" if its parameter-occurrence count
    is strictly greater than its entity-name-occurrence count, and vice
    versa. A packet is ``mostly_param`` if every token is param-favoured
    (even if some token has nonzero name occurrences); ``all_param``
    requires zero name occurrences across the packet. The mostly_*
    bucket catches packets like ``{excludes, hidden, ignore, kernel}``
    where ``kernel`` shows up in function names (e.g. ``find_kernel``)
    but the packet's intent is clearly parameter-bundling.
    """
    if not token_prov:
        return "none"
    any_name = False
    any_param = False
    all_param_favoured = True
    all_name_favoured = True
    for prov in token_prov.values():
        if prov["name"] > 0:
            any_name = True
        if prov["param"] > 0:
            any_param = True
        if prov["param"] <= prov["name"]:
            all_param_favoured = False
        if prov["name"] <= prov["param"]:
            all_name_favoured = False
    if any_param and not any_name:
        return "all_param"
    if any_name and not any_param:
        return "all_name"
    if all_param_favoured and any_param:
        return "mostly_param"
    if all_name_favoured and any_name:
        return "mostly_name"
    if any_name and any_param:
        return "mixed"
    return "none"


def map_packet(
    packet: set[str],
    lexicon: Lexicon,
    *,
    scope: str = "callable",
) -> CorrectiveAction:
    """Classify one pathological packet by token provenance + shape.

    ``scope`` should match the scope the packet was extracted from
    (``"callable"`` or ``"file"``); it influences the advisory text and
    distinguishes file-scope module candidates from callable-scope
    dataclass candidates.
    """
    prov = _token_provenance(lexicon, packet)
    shape = _classify_provenance(prov)
    n = len(packet)

    if n == 2 and shape in ("all_param", "mostly_param"):
        return CorrectiveAction(
            packet=frozenset(packet),
            kind="named_tuple",
            confidence="medium" if shape == "all_param" else "low",
            advisory=(
                f"Pair {sorted(packet)} travels together as parameters. "
                f"Consider a named tuple, dataclass, or kwargs-only signature "
                f"with documentation explaining the pairing."
            ),
            evidence={"size": n, "provenance": shape, "scope": scope,
                      "token_provenance": prov},
        )

    if n >= 3 and shape == "all_param":
        return CorrectiveAction(
            packet=frozenset(packet),
            kind="extract_dataclass",
            confidence="high",
            advisory=(
                f"{n} parameters {sorted(packet)} co-travel across many "
                f"callables. Bundle them into a single dataclass and pass "
                f"the dataclass instance. Textbook FindOptions / RequestContext "
                f"case."
            ),
            evidence={"size": n, "provenance": "all_param", "scope": scope,
                      "token_provenance": prov},
        )

    if n >= 3 and shape == "mostly_param":
        return CorrectiveAction(
            packet=frozenset(packet),
            kind="extract_dataclass",
            confidence="medium",
            advisory=(
                f"{n} tokens {sorted(packet)} co-travel; the majority of "
                f"occurrences are parameters, though some tokens also "
                f"appear in entity names. Bundle into a dataclass — the "
                f"entity-name overlap is likely a wrapper/kernel naming "
                f"echo of the same concept (e.g. find_kernel taking "
                f"FindOptions)."
            ),
            evidence={"size": n, "provenance": "mostly_param", "scope": scope,
                      "token_provenance": prov},
        )

    if n >= 3 and shape == "all_name" and scope == "file":
        return CorrectiveAction(
            packet=frozenset(packet),
            kind="extract_module",
            confidence="high",
            advisory=(
                f"{n} entity-name tokens {sorted(packet)} recur across "
                f"multiple files without a module owning the shared concept. "
                f"Extract a module around the dominant token; move the "
                f"related entities into it."
            ),
            evidence={"size": n, "provenance": "all_name", "scope": scope,
                      "token_provenance": prov},
        )

    if n >= 3 and shape == "mostly_name" and scope == "file":
        return CorrectiveAction(
            packet=frozenset(packet),
            kind="extract_module",
            confidence="medium",
            advisory=(
                f"{n} tokens {sorted(packet)} co-travel across files; the "
                f"majority appear as entity names with some parameter "
                f"echoes. Likely a missing module around the shared "
                f"vocabulary."
            ),
            evidence={"size": n, "provenance": "mostly_name", "scope": scope,
                      "token_provenance": prov},
        )

    if n >= 3 and shape == "mixed" and scope == "file":
        return CorrectiveAction(
            packet=frozenset(packet),
            kind="missing_class",
            confidence="medium",
            advisory=(
                f"Vocabulary {sorted(packet)} spans both entity names and "
                f"parameter signatures across multiple files. The shared "
                f"vocabulary likely indicates a missing class that would "
                f"unify the declarations and the signatures."
            ),
            evidence={"size": n, "provenance": "mixed", "scope": scope,
                      "token_provenance": prov},
        )

    if shape == "mixed" and scope == "callable":
        return CorrectiveAction(
            packet=frozenset(packet),
            kind="naming_convention",
            confidence="medium",
            advisory=(
                f"Tokens {sorted(packet)} co-travel within callable signatures, "
                f"mixing entity names and parameter names. Likely a registry "
                f"or wrapper convention (e.g. `run_X(cfg)` returning `Slop`, "
                f"`add_parser(subparsers)`). Document the convention; consider "
                f"an ABC or protocol to make it enforceable."
            ),
            evidence={"size": n, "provenance": "mixed", "scope": scope,
                      "token_provenance": prov},
        )

    return CorrectiveAction(
        packet=frozenset(packet),
        kind="review",
        confidence="low",
        advisory=(
            f"Packet {sorted(packet)} (n={n}, provenance={shape}, scope={scope}) "
            f"does not match a high-confidence corrective-action category. "
            f"Surface for human review."
        ),
        evidence={"size": n, "provenance": shape, "scope": scope,
                  "token_provenance": prov},
    )


def map_packets_to_actions(
    packets: Iterable[set[str]],
    lexicon: Lexicon,
    *,
    scope: str = "callable",
) -> list[CorrectiveAction]:
    """Apply ``map_packet`` to each packet."""
    return [map_packet(p, lexicon, scope=scope) for p in packets]
