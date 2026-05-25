"""lexical.slackers — sibling functions refusing to align by naming.

Fires on real first-parameter clusters (per the imposters profile)
where the member names don't fit a common token template. The
cluster is a structural family; the names refuse to admit it.

The fix is rename-for-consistency: pick a template
(``verb_param_X``, ``X_param``, etc.) and apply it across the
cluster. Slop catches what humans rarely fix on agent-written
code, because each name reads fine in isolation — only the family
fails to communicate.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from slop.linter.rule_config import RuleConfig
from slop.config import Config
from slop.lexicon.affix import UNIVERSAL_NOISE, Lexeme, build_affix_patterns
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.lexicon.view import Lexicon


_REAL_PROFILES = frozenset({"missing_class", "heterogeneous"})


def _derive_root(lexicon: Lexicon, slop_config: Config) -> Path:
    """Choose the search root.

    Always prefer the longest common directory across the lexicon's
    parsed files. Falls back to slop_config.root when the lexicon is
    empty.
    """
    paths = [p.path for p in lexicon._parses]  # noqa: SLF001
    if paths:
        common = Path(os.path.commonpath([str(p) for p in paths]))
        return common.parent if common.is_file() else common
    if slop_config.root:
        return Path(slop_config.root).expanduser().resolve()
    return Path.cwd()


def run_slackers(
    lexicon: Lexicon, rule_config: RuleConfig, slop_config: Config,
) -> RuleResult:
    """Flag first-parameter clusters whose member names don't align."""
    min_cluster = int(rule_config.params.get("min_cluster", 3))
    raw_exempt = rule_config.params.get("exempt_names", ["self", "cls"])
    exempt_names = frozenset(raw_exempt) if raw_exempt else frozenset()
    max_coverage = float(rule_config.params.get("max_coverage", 0.30))
    severity = rule_config.severity
    root = _derive_root(lexicon, slop_config)

    clusters = lexicon.first_param_clusters(
        min_cluster=min_cluster,
        exempt_names=exempt_names,
        root=root,
    )

    violations: list[Slop] = []
    for cluster in clusters:
        if cluster.profile_label not in _REAL_PROFILES:
            continue
        items = [
            Lexeme.of(name, file=file, line=line)
            for name, file, line in cluster.members
        ]
        patterns = build_affix_patterns(items, exclude=UNIVERSAL_NOISE)
        meaningful = [
            p for p in patterns
            if sum(len(v) for v in p.variants.values()) >= 2
        ]
        covered: set[str] = set()
        for p in meaningful:
            for members in p.variants.values():
                for n, _, _ in members:
                    covered.add(n)
        coverage = len(covered) / len(items) if items else 0.0
        if coverage > max_coverage:
            continue

        _anchor_name, anchor_file, anchor_line = cluster.members[0]
        scope_phrase = (
            f"in `{cluster.scope}`" if cluster.scope_kind == "file"
            else f"under `{cluster.scope}/`" if cluster.scope_kind == "package"
            else "across the codebase"
        )
        member_names = ", ".join(f"`{n}`" for n, _, _ in cluster.members[:5])
        if len(cluster.members) > 5:
            member_names += f" (+{len(cluster.members) - 5})"
        violations.append(Slop(
            rule="lexical.slackers",
            file=anchor_file,
            line=anchor_line,
            symbol=cluster.parameter_name,
            message=(
                f"{len(cluster.members)} functions {scope_phrase} share "
                f"`{cluster.parameter_name}` as first parameter but the "
                f"names don't align ({coverage:.0%} fit any common "
                f"template). Members: {member_names}. The cluster is "
                f"real; the names refuse to admit it. Consider a naming "
                f"template (e.g., `verb_{cluster.parameter_name}` or "
                f"`{cluster.parameter_name}_attribute`) to make the "
                f"family relationship visible."
            ),
            severity=severity,
            value=round(coverage, 3),
            threshold=max_coverage,
            metadata={
                "scope": cluster.scope,
                "scope_kind": cluster.scope_kind,
                "profile_from_imposters": cluster.profile_label,
                "coverage": round(coverage, 3),
                "n_meaningful_patterns": len(meaningful),
                "members": [
                    {"name": n, "file": f, "line": l}
                    for n, f, l in cluster.members
                ],
            },
        ))

    return RuleResult(
        rule="lexical.slackers",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "clusters_detected": len(clusters),
            "violation_count": len(violations),
        },
    )

RULE = RuleDefinition(
    name=Tag.SLACKERS.key,
    category=Tag.SLACKERS.key,
    description='Sibling functions sharing input but refusing to align by naming template',
    default_severity='warning',
    default_enabled=True,
    threshold_label='< 30% template coverage',
    run=run_slackers,
)
