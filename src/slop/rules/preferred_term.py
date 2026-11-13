"""preferred-term: a declared name uses a word the project's vocabulary replaces.

The project's vocabulary (``slop.ontology``) lists, for each defined term, the word to use
(``prefLabel``) and the other words that name it (``altLabel``: synonyms and abbreviations;
``hiddenLabel``: retired words). A class, callable, parameter, property, module or package name
that uses one of those other words breaks the agreed vocabulary, which is objective: it follows
from the name and the stated vocabulary alone (Deissenboeck and Pizka 2006: one concept, one
name). Silent when the project has no vocabulary. The vocabulary arrives on the analysis context
as a ``lexicon.Vocabulary``; this rule never reads the ontology itself.
"""
from __future__ import annotations

from collections.abc import Iterable

from ..config import RuleConfig
from ..lexicon import Vocabulary, split_tokens
from ..rule import Rule
from ..scope.model import Scope
from ..scope.identity import ScopeKind
from ..scope.lexicon import declared_units
from ..violation import Violation

#: kinds visited separately at their own altitude, so a module does not report its package's name
_OWN_ALTITUDE = frozenset({ScopeKind.PACKAGE, ScopeKind.MODULE})


class PreferredTermRule(Rule):
    name = "preferred-term"
    description = "a declared name uses a word the project's vocabulary replaces with its preferred term"
    altitudes = _OWN_ALTITUDE

    def check(self, component: Scope, config: RuleConfig) -> Iterable[Violation]:
        vocabulary = component.context.vocabulary
        if vocabulary is not None:
            yield from _declarations(self.name, component, vocabulary)


def _declarations(rule: str, scope: Scope, vocabulary: Vocabulary) -> Iterable[Violation]:
    """One violation per name ``scope`` and its classes and callables declare that uses a
    replaced word, at the scope that declares it."""
    for name, _role, _span in declared_units(scope):
        replaced = [(word, vocabulary.preferred(word)) for word in split_tokens(name)]
        word, preferred = next(((w, p) for w, p in replaced if p is not None), (None, None))
        if preferred is not None:
            yield Violation.at(scope, rule, f"name '{name}' uses '{word}'; the vocabulary's word is '{preferred}'",
                               value=1, threshold=0)
    for child in scope.children():
        if child.id.kind not in _OWN_ALTITUDE:
            yield from _declarations(rule, child, vocabulary)
