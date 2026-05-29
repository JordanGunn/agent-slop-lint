"""vocabulary — the identifier token space as a claim-free observation.

This rule does not emit a verdict. It emits a single OBSERVATION: the
corpus's identifier token distribution (Zipf fit, hapax floor,
frequency spectrum, dominant concepts), narrated into natural language
for an agent to investigate.

Why an observation, not a verdict: the identifier vocabulary is a Zipf
near-invariant — engineered codebases cluster at α≈0.9 / R²≈0.93 /
hapax≈0.49 regardless of size or discipline (measured; see project
memory). A single scalar like the hapax ratio therefore can't honestly
gate a build — it reads ~0.5 on clean and messy code alike. What the
emitter CAN do is hand an agent the measured distribution plus the
population norm and let it decide whether the shape warrants a look.
This makes no precision claim, so it cannot be a false positive — the
opposite of the verdict rules whose value rides on a discriminator.

The compute lives on the Lexicon view (``Lexicon.token_distribution``);
the natural-language transform lives on the returned ``TokenDistribution``
(``.narrate()``). This rule is the thin emission layer.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.slop import Action, Disposition, Evidence, Slop
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition, RuleResult

if TYPE_CHECKING:
    from slop.lexicon.view import Lexicon


_RULE = Tag.VOCABULARY.key

# Universal scaffolding tokens carry no concept signal; exclude them so the
# distribution reflects domain vocabulary, not boilerplate.
_NOISE = frozenset({
    "get", "set", "to", "from", "of", "for", "is", "as", "the", "a", "an",
    "init", "self", "cls", "run", "main", "args", "kwargs",
})


def _narrate_packages(packages, min_distinct: int) -> str:
    """A claim-free listing of packages by one-off-vocabulary density.

    Deliberately a ranked listing, not a deviation-vs-norm verdict: it
    reports each package's measured hapax ratio (behind the distinct-token
    floor) and lets the agent decide where to look. No "denser than norm"
    adjectives — the per-package ratio is noisier than the global scalar it
    derives from, and there is no validated per-package cutoff.
    """
    if len(packages) < 2:
        return ""
    shown = ", ".join(
        f"{pkg} {d.hapax_ratio:.2f}" for pkg, d in packages[:6]
    )
    return (
        f"Per-package one-off-vocabulary density (≥{min_distinct} distinct "
        f"tokens), highest first: {shown}. Higher = more identifiers used "
        f"once relative to the package's own vocabulary; inspect the densest "
        f"if reviewing fragmentation."
    )


def run(
    lexicon: "Lexicon", rule_config: Rule, slop_config: Config,
) -> RuleResult:
    """Emit one observation describing the identifier token distribution."""
    top = int(rule_config.params.get("top_tokens", 15))
    pkg_min_distinct = int(rule_config.params.get("package_min_distinct", 40))
    severity = rule_config.severity

    dist = lexicon.token_distribution(top=top, exclude=_NOISE)

    if dist.distinct == 0:
        return RuleResult(
            rule=_RULE,
            status="pass",
            summary={"tokens_analyzed": 0},
        )

    # Within-namespace decomposition: per-package hapax density. A flat
    # global distribution is a Zipf near-invariant; the variance lives
    # within the codebase, across its packages. This is a raw ranked
    # listing (instrumentation), NOT a deviation-vs-norm verdict.
    packages = lexicon.package_distributions(
        min_distinct=pkg_min_distinct, exclude=_NOISE,
    )
    per_package = [
        {"package": pkg, "hapax_ratio": round(d.hapax_ratio, 3),
         "distinct": d.distinct}
        for pkg, d in packages
    ]

    data = dist.as_dict()
    data["per_package"] = per_package
    data["package_min_distinct"] = pkg_min_distinct

    message = dist.narrate()
    within = _narrate_packages(packages, pkg_min_distinct)
    if within:
        message = f"{message} {within}"

    observation = Slop(
        rule=_RULE,
        file=str(slop_config.root or "."),
        line=None,
        symbol=None,
        message=message,
        severity=severity,
        scope=None,
        disposition=Disposition.OBSERVATION,
        action=Action.INVESTIGATE,
        evidence=Evidence(kind="token-distribution", data=data),
        value=round(dist.hapax_ratio, 3),
        metadata={"kind": "token-distribution"},
    )

    return RuleResult(
        rule=_RULE,
        status="pass",
        observations=[observation],
        summary={
            "tokens_analyzed": dist.n,
            "distinct_tokens": dist.distinct,
            "hapax_ratio": round(dist.hapax_ratio, 3),
            "zipf_alpha": round(dist.zipf_alpha, 3),
            "zipf_r2": round(dist.zipf_r2, 3),
            "packages_analyzed": len(per_package),
        },
    )


RULE = RuleDefinition(
    name=_RULE,
    category=_RULE,
    description="Identifier token distribution (Zipf/hapax) — claim-free observation, no verdict",
    default_severity="info",
    default_enabled=True,
    threshold_label="observation (no threshold)",
    run=run,
    view="lexicon",
)
