"""Research diagnostic suite — composes violation accounting + distribution shape.

The subpackage that emits structured, JSON-serialisable diagnostic
data for observation documents. Three modules:

- ``violations`` — multi-scope violation counts + rule × cell cross-tab
- ``distribution`` — histogram primitives + Summary statistics
- (this module) ``report()`` — composes them into one report dict

The report is intentionally observation-internal and versionless — per
R5 in the IRIS contract, locking a schema before consumers are known
would over-commit. Treat the dicts as adhoc until the consumer set
stabilises.

See ``docs/research/observations/`` for the consumers.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, TYPE_CHECKING

from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.types import RuleDefinition

from slop.lexicon.diagnostic.distribution import (
    HistogramBin, Summary, TokenDistribution,
    histogram_buckets, log_buckets, summary, token_distribution,
)
from slop.lexicon.diagnostic.violations import (
    ScopedViolationCount, ViolationCell,
    count_by_scope, with_cells, tabulate_cells, format_cells,
)

if TYPE_CHECKING:
    from slop.lexicon.view import Lexicon


__all__ = [
    # distribution
    "HistogramBin", "Summary", "TokenDistribution",
    "histogram_buckets", "log_buckets", "summary", "token_distribution",
    # violations
    "ScopedViolationCount", "ViolationCell",
    "count_by_scope", "with_cells", "tabulate_cells", "format_cells",
    # composed
    "report",
]


def report(
    lexicon: Lexicon,
    *,
    rule_defs: Iterable[RuleDefinition] | None = None,
    rule_configs: Mapping[str, Rule] | None = None,
    slop_config: Config | None = None,
    root: Path | None = None,
    class_vocabularies: Mapping[str, set[str]] | None = None,
    exclude_tokens: frozenset[str] = frozenset(),
    packet_min_bags: int = 5,
    packet_min_association: float = 0.7,
) -> dict[str, Any]:
    """Compose the full diagnostic dict for one corpus.

    Sections:
      - ``corpus``: file counts, callable counts
      - ``distributions``: token-frequency, sprawl token-spread, packet sizes
      - ``packets``: callable-scope + file-scope packets, pathological vs
        conventional (when class_vocabularies is supplied)
      - ``violations_by_scope``: per-scope violation counts when
        rule_defs + rule_configs + slop_config are supplied

    The dict is JSON-serialisable. Intentionally schema-versionless;
    consumers should be defensive.
    """
    from slop.lexicon.filters import split_packets_by_class_ownership

    files = list(lexicon.files())
    callables = list(lexicon.callables())

    freq = lexicon.frequencies(exclude=exclude_tokens)
    locs = lexicon.token_locations(exclude=exclude_tokens)

    dist_freq = summary(
        list(freq.values()), name="token_occurrence_count", log_bins=True,
    )
    dist_sprawl = summary(
        [len(files) for files in locs.values()],
        name="token_file_spread", log_bins=True,
    )

    callable_packets = lexicon.packets(
        scope="callable", min_bags=packet_min_bags,
        min_association=packet_min_association, exclude=exclude_tokens,
    )
    file_packets = lexicon.packets(
        scope="file", min_bags=packet_min_bags,
        min_association=packet_min_association, exclude=exclude_tokens,
    )

    dist_packet_callable = summary(
        [len(p) for p in callable_packets],
        name="packet_size_callable_scope",
    )
    dist_packet_file = summary(
        [len(p) for p in file_packets],
        name="packet_size_file_scope",
    )

    packets_section: dict[str, Any] = {
        "thresholds": {
            "min_bags": packet_min_bags,
            "min_association": packet_min_association,
        },
        "callable_scope": {
            "total": len(callable_packets),
            "packets": [sorted(p) for p in callable_packets],
        },
        "file_scope": {
            "total": len(file_packets),
            "packets": [sorted(p) for p in file_packets],
        },
    }

    if class_vocabularies is not None:
        from slop.lexicon.actions import map_packets_to_actions

        path_c, conv_c = split_packets_by_class_ownership(
            callable_packets, dict(class_vocabularies),
        )
        path_f, conv_f = split_packets_by_class_ownership(
            file_packets, dict(class_vocabularies),
        )
        actions_c = map_packets_to_actions(path_c, lexicon, scope="callable")
        actions_f = map_packets_to_actions(path_f, lexicon, scope="file")
        packets_section["callable_scope"]["pathological"] = [
            a.as_dict() for a in actions_c
        ]
        packets_section["callable_scope"]["conventional"] = [
            {"packet": sorted(p), "class": cls} for p, cls in conv_c
        ]
        packets_section["file_scope"]["pathological"] = [
            a.as_dict() for a in actions_f
        ]
        packets_section["file_scope"]["conventional"] = [
            {"packet": sorted(p), "class": cls} for p, cls in conv_f
        ]

    out: dict[str, Any] = {
        "corpus": {
            "files": len(files),
            "callables": len(callables),
            "distinct_tokens": len(freq),
        },
        "thresholds": {
            "exclude_tokens": sorted(exclude_tokens),
        },
        "distributions": {
            "token_occurrence_count": dist_freq.as_dict(),
            "token_file_spread": dist_sprawl.as_dict(),
            "packet_size_callable_scope": dist_packet_callable.as_dict(),
            "packet_size_file_scope": dist_packet_file.as_dict(),
        },
        "packets": packets_section,
    }

    if rule_defs is not None and rule_configs is not None and slop_config is not None:
        scopes_section: dict[str, list[dict[str, Any]]] = {}
        for axis in ("file", "package", "root", "callable"):
            counts = count_by_scope(
                lexicon, rule_defs,
                rule_configs=rule_configs, slop_config=slop_config,
                scope=axis, root=root,
            )
            scopes_section[axis] = [
                {"rule": c.rule, "key": c.key, "count": c.count} for c in counts
            ]
        out["violations_by_scope"] = scopes_section

    return out
