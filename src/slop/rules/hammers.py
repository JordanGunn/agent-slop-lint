"""lexical.hammers — institutionalised catch-all vocabulary (observation).

"When all you have is a hammer, everything looks like a nail." ``Manager``,
``Helper``, ``Util``, ``Data``, ``Object``, ``Thing`` are the nouns a codebase reaches
for when it has no real domain term — hammering every responsibility into the same
shape.

Disposition (a deliberate departure from the legacy per-name banlist verdict): flagging
a single ``DataManager`` is a style nit an agent fixes on sight, not structural debt
(structural-not-style). What *is* structural is **institutionalisation** — a hammer term
that recurs across many files and bonds with no specific concept (a packet-isolate),
i.e. the codebase systematically lacks domain vocabulary in that area. slop can measure
that, but it cannot honestly prescribe *which* domain term to use. So hammers is an
``OBSERVATION``: one investigate-nudge per institutionalised hammer term, evidence not
verdict. The banlist only scopes *which* generic terms count.

``min_spread`` (default 3) gates institutionalisation. A hammer term used in one or two
places is not surfaced.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Evidence, Finding, Observation
from ..metrics.lexical import Lexical
from ..metrics.lexical.affix import UNIVERSAL_NOISE
from ..metrics.locus import narrowest_common_ancestor
from ..rule import Rule

# Lowercased catch-all vocabulary (legacy DEFAULT_PROFILE). The banlist scopes which
# tokens are "generic"; institutionalisation (spread + isolate) decides what surfaces.
_HAMMERS = frozenset({
    "manager", "coordinator", "helper", "utility", "util", "utils", "handler",
    "processor", "service", "provider", "engine", "factory", "builder", "wrapper",
    "adapter", "spec", "specification", "base", "abstract", "object", "item",
    "element", "thing", "things", "data", "info", "container", "holder", "common",
    "core", "misc", "extra", "shared", "stuff",
})


def _scope_index(component) -> dict:
    """Map every scope's ScopeId to the scope, so a NamedEntity's ``locus`` can be
    resolved back to the owner-chain-bearing scope the NCA walk needs."""
    by_id: dict = {}

    def walk(s) -> None:
        by_id[s.id] = s
        for ch in s.children():
            walk(ch)

    walk(component)
    return by_id


class HammersRule(Rule):
    name = "lexical.hammers"
    altitudes = frozenset({ScopeKind.CORPUS})

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(name=cls.name, params={"min_spread": 3, "terms": sorted(_HAMMERS)})

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        min_spread = int(config.param("min_spread", 3))
        terms = frozenset(t.lower() for t in config.param("terms", sorted(_HAMMERS)))

        lx = Lexical.over(component)
        spread = {t: len(files) for t, files in lx.token_locations().items()}
        isolates = {t for t, _ in lx.packet_isolates(
            min_bags=3, min_association=0.7, min_frequency=min_spread, exclude=UNIVERSAL_NOISE)}
        scope_by_id = _scope_index(component)

        # Which entities each hammer term names — kept as scopes so the term can be
        # attributed to the narrowest scope its carriers share (a package if the
        # institutionalisation is local), not blanket-pinned to the corpus.
        carriers: dict[str, list] = {}
        for entity in lx.named_entities():
            for tok in entity.tokens:
                tl = tok.lower()
                if tl in terms:
                    carriers.setdefault(tl, []).append(entity)

        for term in sorted(carriers):
            files = spread.get(term, 0)
            if files < min_spread or term not in isolates:
                continue  # not institutionalised (rare, or it bonds with a real concept)
            entities = carriers[term]
            names = [e.name for e in entities]
            carrier_scopes = [scope_by_id[e.locus] for e in entities if e.locus in scope_by_id]
            nca = narrowest_common_ancestor(carrier_scopes)
            yield Observation(
                rule=self.name,
                component=nca.id if nca is not None else component.id,
                evidence=Evidence(kind="hammer", data={
                    "term": term, "file_spread": files, "entity_count": len(names),
                    "examples": sorted(set(names))[:8]}),
                message=(
                    f"the catch-all term '{term}' names {len(names)} entities across {files} "
                    "files and bonds with no specific concept — the codebase may lack a domain "
                    f"term here (e.g. {', '.join(sorted(set(names))[:3])}). Consider a name that "
                    "says what it is, not what shape it has."
                ),
            )
