"""lexical.confusion — file holds multiple independent cohesive units.

A file is "confused" when its top-level functions partition into two or
more **disjoint call-islands**: groups that transitively share callees
within the group but not across groups. That is the coordinator-over-
islands (grab-bag) topology — the file is doing the work of several
cohesive units that merely share a namespace.

Detection (the primary signal) is structural, not lexical: it consumes
``Structure.redundancy_clusters`` — per-file connected components of the
``redundancy`` rule's sibling-callee pairs. Two disjoint clusters = two
call-islands. This supersedes the earlier first-parameter-receiver +
vocabulary-Jaccard heuristic, which was a weak proxy (see
project_grabbag_battery / project_confusion_topology). The receiver
clusters are kept only as *corroboration* that raises confidence.

Detecting ≥2 call-islands proves the file is *partitionable*; it does not
prove the file *should* be split — a coordinated pipeline (one function
bridging the islands) and a true grab-bag (disconnected islands) look
identical at the cluster level. The should-split discriminator is the
connected-component structure of the file's full intra-file call graph
(``Structure.intra_file_call_components``): if the islands all fall in one
component, a coordinator bridges them — a cohesive pipeline, suppressed;
if they span two or more components, nothing connects them — a genuine
disconnected grab-bag. Because the coordinator test has already run, a
confirmed grab-bag earns a deterministic ``SPLIT_MODULE`` rather than a
hedged review.

Adapts Lanza & Marinescu's (2006) detection-strategy framework from OO
classes to module-level free-function code.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from slop.linter.rule import Rule
from slop.config import Config
from slop.lexicon.tokens import split_tokens
from slop.lexicon.affix import UNIVERSAL_NOISE
from slop.linter.slop import Action, Slop
from slop.linter.types import RuleResult
from slop.tree.records import CallableKind
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.lexicon.view import Lexicon


from slop.linter.rules.roots import derive_root as _derive_root


_RULE = Tag.CONFUSION.key

# Receiver-cluster profiles that count as substantive corroboration. A
# cluster is substantive when it represents a real cohesive unit, not
# exempt-name plumbing or infrastructure threaded through the file.
_SUBSTANTIVE_PROFILES = frozenset({
    "missing_class", "dispatch_family", "strategy_family",
    "heterogeneous",
})


def _functions_per_file(lexicon: Lexicon, root: Path) -> dict[str, int]:
    """Count emittable functions per file-relative path."""
    counts: dict[str, int] = {}
    for c in lexicon.callables():
        if c.kind == CallableKind.LAMBDA:
            continue
        try:
            rel = str(c.path.relative_to(root))
        except ValueError:
            rel = str(c.path)
        counts[rel] = counts.get(rel, 0) + 1
    return counts


def _name_line_index(lexicon: Lexicon, root: Path) -> dict[tuple[str, str], int]:
    """Map ``(rel_file, simple_name) -> line`` for finding anchors."""
    index: dict[tuple[str, str], int] = {}
    for c in lexicon.callables():
        try:
            rel = str(c.path.relative_to(root))
        except ValueError:
            rel = str(c.path)
        simple = c.qualname.rsplit(".", 1)[-1]
        index.setdefault((rel, simple), c.line)
    return index


def _name_tokens(names: frozenset[str]) -> set[str]:
    """Union of lowercased name-tokens across a set of function names."""
    out: set[str] = set()
    for name in names:
        for t in split_tokens(name):
            tl = t.lower()
            if tl not in UNIVERSAL_NOISE:
                out.add(tl)
    return out


def _cross_island_jaccard(islands: list[frozenset[str]]) -> float:
    """Mean pairwise Jaccard over island name-token sets.

    Low overlap = islands name disjoint concerns (grab-bag-leaning).
    High overlap = islands share vocabulary (pipeline-phase-leaning).
    Informational only — it does NOT switch the verdict (see module
    docstring on why detecting islands ≠ should-split).
    """
    if len(islands) < 2:
        return 0.0
    token_sets = [_name_tokens(i) for i in islands]
    pairs: list[float] = []
    for i in range(len(token_sets)):
        for j in range(i + 1, len(token_sets)):
            a, b = token_sets[i], token_sets[j]
            if not a and not b:
                pairs.append(1.0)
            elif not a or not b:
                pairs.append(0.0)
            else:
                pairs.append(len(a & b) / len(a | b))
    return sum(pairs) / len(pairs) if pairs else 0.0


def run(
    lexicon: Lexicon, rule_config: Rule, slop_config: Config,
) -> RuleResult:
    """Flag files whose functions split into ≥2 disjoint call-islands."""
    min_functions = int(rule_config.params.get("min_functions", 5))
    min_islands = int(rule_config.params.get("min_islands", 2))
    min_shared = int(rule_config.params.get("min_shared", 3))
    min_score = float(rule_config.params.get("min_score", 0.5))
    min_island_size = int(rule_config.params.get("min_island_size", 2))
    # Receiver-cluster corroboration params (Lexicon side).
    min_cluster_size = int(rule_config.params.get("min_cluster_size", 3))
    raw_exempt = rule_config.params.get("exempt_names", ["self", "cls"])
    exempt_names = frozenset(raw_exempt) if raw_exempt else frozenset()
    severity = rule_config.severity
    root = _derive_root(lexicon, slop_config)

    def _rel(p) -> str:
        try:
            return str(Path(p).relative_to(root))
        except ValueError:
            return str(p)

    # Primary signal: per-file disjoint redundancy clusters (call-islands).
    # Built from a Structure over the same parses the Lexicon wraps — the
    # grab-bag battery is inherently cross-substrate (structural cohesion +
    # lexical receivers), so the rule computes both halves itself.
    from slop.structure.view import Structure

    structure = Structure(lexicon._parses)  # noqa: SLF001 — shared parse substrate
    clusters_abs = structure.redundancy_clusters(
        min_shared=min_shared, min_score=min_score,
    )
    # Should-split discriminator: connected components of each file's
    # intra-file call graph. Islands in one component are coordinator-
    # bridged (cohesive pipeline → suppress); islands spanning ≥2
    # components are genuinely disconnected (grab-bag → emit).
    components_abs = structure.intra_file_call_components()

    # Corroboration: substantive first-parameter receiver clusters per file.
    receiver_by_file: dict[str, list] = {}
    for c in lexicon.first_param_clusters(
        min_cluster=min_cluster_size, exempt_names=exempt_names, root=root,
    ):
        if c.scope_kind != "file":
            continue
        if c.profile_label in _SUBSTANTIVE_PROFILES:
            receiver_by_file.setdefault(c.scope, []).append(c)

    functions_per_file = _functions_per_file(lexicon, root)
    line_index = _name_line_index(lexicon, root)
    files_searched = len(functions_per_file)
    functions_analyzed = sum(functions_per_file.values())

    candidate_files = 0
    violations: list[Slop] = []
    for abs_file, raw_islands in sorted(clusters_abs.items()):
        islands = [c for c in raw_islands if len(c) >= min_island_size]
        if len(islands) < min_islands:
            continue
        file = _rel(abs_file)
        n_functions = functions_per_file.get(file, 0)
        if n_functions < min_functions:
            continue
        candidate_files += 1

        # Discriminator: how many distinct call-components do the islands
        # occupy? One ⇒ a coordinator bridges them (cohesive pipeline) ⇒
        # suppress. Two or more ⇒ disconnected concerns ⇒ genuine grab-bag.
        components = components_abs.get(abs_file, [])
        comp_of: dict[str, int] = {}
        for idx, comp in enumerate(components):
            for name in comp:
                comp_of[name] = idx
        island_components = {
            comp_of[m] for isl in islands for m in isl if m in comp_of
        }
        if len(island_components) < 2:
            continue  # coordinator-bridged → cohesive pipeline, leave it

        islands_sorted = sorted(islands, key=lambda m: (-len(m), sorted(m)))
        members_flat = [name for isl in islands_sorted for name in isl]
        anchor = min(
            (line_index.get((file, name), 1) for name in members_flat),
            default=1,
        )
        cross_j = _cross_island_jaccard(islands_sorted)
        receivers = receiver_by_file.get(file, [])
        corroborated = len(receivers) > 0

        boundary = " | ".join(
            "{" + ", ".join(sorted(m)) + "}" for m in islands_sorted
        )
        corroboration_note = (
            f" Corroborated by {len(receivers)} substantive receiver "
            f"cluster(s) ("
            + ", ".join(f"`{c.parameter_name}`" for c in receivers)
            + ")."
            if corroborated else
            " (Structural signal only — no receiver-cluster corroboration.)"
        )
        prescription = (
            f"Split `{file}` into sibling modules along these boundaries: "
            f"{boundary}. The functions form {len(islands_sorted)} call-islands "
            f"in {len(island_components)} disconnected components of the "
            f"intra-file call graph — no function bridges them, so they are "
            f"independent concerns sharing a namespace, not phases of one "
            f"pipeline.{corroboration_note}"
        )

        # The coordinator test has already run: a confirmed disconnected
        # grab-bag earns a deterministic split. Receiver-cluster
        # corroboration lifts confidence further.
        confidence = 0.8 if corroborated else 0.7

        violations.append(Slop(
            rule=_RULE,
            file=file,
            line=anchor,
            symbol=file,
            message=(
                f"`{file}` ({n_functions} functions) splits into "
                f"{len(islands_sorted)} disconnected call-islands "
                f"(no bridging coordinator; cross-island name Jaccard "
                f"{cross_j:.2f}). "
                f"{'Receiver-cluster corroborated.' if corroborated else 'Structural signal only.'}"
            ),
            severity=severity,
            value=len(islands_sorted),
            threshold=min_islands,
            action=Action.SPLIT_MODULE,
            prescription=prescription,
            confidence=confidence,
            metadata={
                "function_count": n_functions,
                "islands": [sorted(m) for m in islands_sorted],
                "call_components": len(island_components),
                "cross_island_jaccard": round(cross_j, 3),
                "receiver_corroboration": [
                    {"param": c.parameter_name, "profile": c.profile_label}
                    for c in receivers
                ],
            },
        ))

    return RuleResult(
        rule=_RULE,
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "files_searched": files_searched,
            "functions_checked": functions_analyzed,
            "candidate_files": candidate_files,
            "violation_count": len(violations),
        },
        errors=[],
    )


RULE = RuleDefinition(
    name=_RULE,
    category=_RULE,
    description='File splits into ≥2 disjoint call-islands (review for grab-bag split)',
    default_severity='warning',
    default_enabled=True,
    threshold_label='≥ 2 disjoint call-islands',
    run=run,
)
