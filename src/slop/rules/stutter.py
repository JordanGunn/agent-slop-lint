"""lexical.stutter — a name restating its enclosing scope (verdict).

``UserManager.get_user_id`` stutters: the ``user`` token is already supplied by the
enclosing class, so the method name repeats context the scope provides. The reader pays
for the redundancy at every call site.

v3 reads the stutter off the *scope tree* directly: a component's enclosing scopes are
its owner chain (class → module → package), so the rule walks ancestors nearest-first
and flags the deepest one whose name tokens overlap the component's own — no manual AST
scope-stack walk (the legacy's approach) is needed. The fix is directed and mechanical —
drop the tokens the scope already says — so this is a ``DROP_REDUNDANT_TOKENS`` verdict.

Noise tokens (Newman 14 + glue) are excluded so a shared ``id``/``data`` does not count;
``min_overlap_tokens`` (default 1) is the canonical single-token stutter.

Calibration (measured on the v1.2.0 snapshot): of 129 stutters, 126 are module-level
(``load_config`` in ``config``, ``git_log`` in ``git``) and only 1 is class-level. These
are technically correct — none is degenerate, every name drops to a valid shorter form,
and the stdlib standard is ``json.load`` not ``json.json_load`` — so the default is kept
honest (a high count on slopped code is the signal, not over-firing). But the *enclosing*
scopes that count are configurable via ``enclosing_scopes``: a project that judges
module-level stutter idiomatic can set ``["class"]`` to keep only the strongest tier,
rather than softening the shipped default.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..scope.base import Scope
from ..scope.identity import ScopeKind
from ..config import RuleConfig
from ..finding import Action, Finding, Severity, Verdict
from ..lexicon.tokenize import split_tokens
from ..metrics.lexical.affix import UNIVERSAL_NOISE
from ..rule import Rule

_KIND_BY_LABEL = {
    "class": ScopeKind.CLASS, "module": ScopeKind.MODULE, "package": ScopeKind.PACKAGE,
}


def _tokens(name: str) -> set[str]:
    return {t.lower() for t in split_tokens(name) if t.lower() not in UNIVERSAL_NOISE}


class StutterRule(Rule):
    name = "lexical.stutter"
    altitudes = frozenset({ScopeKind.CORPUS})

    @classmethod
    def default_config(cls) -> RuleConfig:
        return RuleConfig(name=cls.name, severity=Severity.WARNING,
                          params={"min_overlap_tokens": 1, "check_classes": True,
                                  "enclosing_scopes": ["class", "module", "package"]})

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Finding]:
        min_overlap = int(config.param("min_overlap_tokens", 1))
        check_classes = bool(config.param("check_classes", True))
        enclosing = {_KIND_BY_LABEL[k]
                     for k in config.param("enclosing_scopes", list(_KIND_BY_LABEL))
                     if k in _KIND_BY_LABEL}

        entities = list(component._iter_callables())
        if check_classes:
            entities += list(component._iter_classes())

        for entity in entities:
            if entity.name.startswith("<"):
                continue
            own = _tokens(entity.name)
            if not own:
                continue
            # nearest enclosing scope (owner chain) whose name overlaps
            owner = entity.owner
            while owner is not None:
                if owner.KIND in enclosing:
                    overlap = own & _tokens(owner.name)
                    if len(overlap) >= min_overlap:
                        shared = ", ".join(sorted(overlap))
                        yield Verdict(
                            rule=self.name, component=entity.id, line=entity.line,
                            action=Action.DROP_REDUNDANT_TOKENS,
                            prescription=(
                                f"Drop {{{shared}}} from '{entity.name}': the enclosing "
                                f"{owner.KIND.value} '{owner.name}' already provides it. The "
                                "name restates context the scope supplies."
                            ),
                            severity=config.severity, value=len(overlap), threshold=min_overlap,
                            message=(
                                f"'{entity.name}' restates its {owner.KIND.value} "
                                f"'{owner.name}' (shared: {shared})"
                            ),
                            metadata={"name": entity.name, "enclosing": owner.name,
                                      "enclosing_kind": owner.KIND.value, "shared": sorted(overlap)},
                        )
                        break  # deepest stutter only
                owner = owner.owner
