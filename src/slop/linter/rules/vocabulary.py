"""vocabulary — the identifier token space as a claim-free observation.

This rule does not emit a verdict. It emits a single OBSERVATION: the
corpus's identifier token distribution, decomposed three ways, narrated
into natural language for an agent to investigate.

  1. GLOBAL (Zipf fit, hapax floor, dominant concepts) — a Zipf
     near-invariant, so it serves only as a population-norm anchor.
  2. WITHIN-namespace — per-package hapax density; the within-codebase
     variance the flat global bag collapses.
  3. ACROSS-namespace — per-token owner concentration, with the structural
     import graph gating owner-displacement (a token whose lexical owner
     merely IMPORTS its eponymous package is a legitimate consumer, not an
     escape). This is why the rule is cross-view (``view="tree"``):
     lexical ownership alone can't tell reinvention from consumption.

Why an observation, not a verdict: the identifier vocabulary is a Zipf
near-invariant — engineered codebases cluster at α≈0.9 / R²≈0.93 /
hapax≈0.49 regardless of size or discipline (measured; see project
memory). No scalar here honestly gates a build. The emitter hands the
agent the measured decomposition and lets it decide — it makes no
precision claim, so it cannot be a false positive.

Compute lives on the views (``Lexicon.token_distribution`` /
``.package_distributions`` / ``.concept_ownership``,
``Structure.dependency_graph``); narration transforms live on the
returned records. This rule is the thin emission layer.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.slop import Action, Disposition, Evidence, Slop
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition, RuleResult

if TYPE_CHECKING:
    from slop.tree.tree import Tree


_RULE = Tag.VOCABULARY.key

# How many leading tokens to analyse for cross-package ownership.
_OWNERSHIP_TOP = 20

# Universal scaffolding tokens carry no concept signal; exclude them so the
# distribution reflects domain vocabulary, not boilerplate.
_NOISE = frozenset({
    "get", "set", "to", "from", "of", "for", "is", "as", "the", "a", "an",
    "init", "self", "cls", "run", "main", "args", "kwargs",
})


def _narrate_ownership(ownership) -> str:
    """Claim-free narration of cross-package concept ownership.

    The only actionable class is ``displaced_unexplained``: a token that
    names a package but is owned elsewhere WITHOUT the owner importing that
    package (so the owner can't be a mere consumer). Cohesive and
    cross-cutting counts are reported as context, not as a claim.
    """
    if not ownership:
        return ""
    buckets: dict[str, list] = {}
    for o in ownership:
        buckets.setdefault(o.verdict(), []).append(o)
    cohesive = len(buckets.get("cohesive", []))
    crosscut = len(buckets.get("cross_cutting", []))
    unexplained = buckets.get("displaced_unexplained", [])
    parts = [
        f"Concept ownership (top {len(ownership)} tokens): {cohesive} cohesive, "
        f"{crosscut} cross-cutting plumbing, {len(unexplained)} displaced from "
        f"their eponymous package without an import link."
    ]
    if unexplained:
        cases = "; ".join(
            f"`{o.token}` (owned by `{o.owner}`, not `{o.token}/`; "
            f"`{o.owner}` doesn't import `{o.token}/`)"
            for o in unexplained[:5]
        )
        parts.append(
            f"Unexplained displacement worth inspecting: {cases}. The owner "
            f"uses the concept's name but has no dependency on the package "
            f"that owns it — check whether it reinvents rather than reuses."
        )
    return " ".join(parts)


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
        f"tokens), highest first: {shown}. Higher density means more "
        f"identifiers used once within the package — which can be "
        f"fragmentation OR legitimate concept diversity (a registry/rules "
        f"package where each module defines a distinct concept reads high "
        f"too); the ratio alone does not distinguish them."
    )


def run(
    tree: "Tree", rule_config: Rule, slop_config: Config,
) -> RuleResult:
    """Emit one observation describing the identifier token distribution.

    Cross-view (``view="tree"``): the global + within-namespace axes come
    from the Lexicon; the across-namespace owner-displacement gate needs the
    Structure import graph.
    """
    from slop.lexicon.diagnostic import namespace

    lexicon = tree.lexicon
    top = int(rule_config.params.get("top_tokens", 15))
    pkg_min_distinct = int(rule_config.params.get("package_min_distinct", 40))
    severity = rule_config.severity

    dist = namespace.token_distribution(lexicon, top=top, exclude=_NOISE)

    if dist.distinct == 0:
        return RuleResult(
            rule=_RULE,
            status="pass",
            summary={"tokens_analyzed": 0},
        )

    # Within-namespace decomposition: per-package hapax density. A flat
    # global distribution is a Zipf near-invariant; the variance lives
    # within the codebase, across its packages. Raw ranked listing
    # (instrumentation), NOT a deviation-vs-norm verdict.
    packages = namespace.package_distributions(
        lexicon, min_distinct=pkg_min_distinct, exclude=_NOISE,
    )
    per_package = [
        {"package": pkg, "hapax_ratio": round(d.hapax_ratio, 3),
         "distinct": d.distinct}
        for pkg, d in packages
    ]

    # Across-namespace: per-token owner concentration, with the import graph
    # gating owner-displacement (owner that imports the eponymous package is
    # a legitimate consumer, not an escape). Only unexplained displacement
    # is signal.
    ownership = namespace.concept_ownership(
        lexicon, tree.structure.dependency_graph(),
        exclude=_NOISE, top=_OWNERSHIP_TOP,
    )

    data = dist.as_dict()
    data["per_package"] = per_package
    data["package_min_distinct"] = pkg_min_distinct
    data["concept_ownership"] = [o.as_dict() for o in ownership]

    message = dist.narrate()
    within = _narrate_packages(packages, pkg_min_distinct)
    if within:
        message = f"{message} {within}"
    across = _narrate_ownership(ownership)
    if across:
        message = f"{message} {across}"

    displaced = sum(1 for o in ownership if o.verdict() == "displaced_unexplained")

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
            "displaced_concepts": displaced,
        },
    )


RULE = RuleDefinition(
    name=_RULE,
    category=_RULE,
    description="Identifier token distribution (Zipf/hapax + namespace decomposition) — claim-free observation, no verdict",
    default_severity="info",
    default_enabled=True,
    threshold_label="observation (no threshold)",
    run=run,
    view="tree",
)
