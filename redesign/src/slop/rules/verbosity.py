"""lexical.verbosity — entity names compensating for a missing namespace (verdict).

Defined at ``{Corpus}`` (the scope-leak signal needs corpus-wide token spread). A long
function/class name is often a class-without-class: ``check_required_binaries`` is three
tokens because the namespace it should live in does not exist. The smell is structural —
the name shoulders disambiguation work the scope should do.

slop ships only the *scope-leak* case: an over-long name whose tokens are both
high-spread (appear across many files) and frequency-head members. That corroboration —
long name + globally-spread tokens — is the structural signal (the name is leaking scope
boundaries), so it is a directed ``NARROW_SCOPE`` verdict.

The legacy also emitted a "local verbosity" note for long-but-locally-scoped names
("may just be a long descriptive name", confidence 0.4). That is a non-actionable style
nudge, not a defect — it is cut here (structural-not-style): slop should not flag a name
it cannot claim is wrong.

A leading language-id token (``_python_walk`` → ``walk``) encodes which grammar a
polyglot helper belongs to, not content, so it is discounted from the token count; the
id set is the corpus's own realm languages.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Action, Finding, Severity, Verdict
from ..metrics.lexical import Lexical
from ..metrics.lexical.affix import UNIVERSAL_NOISE
from ..rule import Rule


class VerbosityRule(Rule):
    name = "lexical.verbosity"
    altitudes = frozenset({ScopeKind.CORPUS})

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(
            name=cls.name, severity=Severity.WARNING,
            params={"max_tokens": 3, "check_classes": True, "min_mean_spread": 5.0},
        )

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        max_tokens = int(config.param("max_tokens", 3))
        check_classes = bool(config.param("check_classes", True))
        min_mean_spread = float(config.param("min_mean_spread", 5.0))

        lx = Lexical.over(component)
        spread = {t: len(files) for t, files in lx.token_locations().items()}
        head = frozenset(t for t, _ in lx.frequency_head())
        lang_ids = {r.language for r in component.realms()} if hasattr(component, "realms") else set()

        for entity in lx.named_entities():
            if entity.kind == "class" and not check_classes:
                continue
            toks = list(entity.tokens)
            if toks and toks[0].lower() in lang_ids:
                toks = toks[1:]
            if len(toks) <= max_tokens:
                continue
            spreads = [spread.get(t.lower(), 0) for t in toks if t.lower() not in UNIVERSAL_NOISE]
            mean_spread = sum(spreads) / len(spreads) if spreads else 0.0
            head_count = sum(1 for t in toks if t.lower() in head)
            if not (mean_spread >= min_mean_spread and head_count >= len(toks) // 2):
                continue  # not a scope-leak — cut (local verbosity is not a defect)
            yield Verdict(
                rule=self.name,
                component=component.id,
                action=Action.NARROW_SCOPE,
                prescription=(
                    f"Move {entity.kind} '{entity.name}' into a narrower namespace: its "
                    f"{len(toks)} name-tokens average {mean_spread:.0f}-file spread and "
                    f"{head_count} are frequency-head tokens — the scope is too loose and "
                    "the name is shouldering disambiguation the scope should do."
                ),
                severity=config.severity,
                value=len(toks),
                threshold=max_tokens,
                line=entity.line,
                message=(
                    f"{entity.kind} '{entity.name}' has {len(toks)} high-spread tokens "
                    f"(mean spread {mean_spread:.0f}) — name compensating for missing scope"
                ),
                metadata={"name": entity.name, "kind": entity.kind, "file": entity.file,
                          "tokens": list(entity.tokens), "mean_spread": round(mean_spread, 1)},
            )
