"""Read and write an Open Ontology model's JSON IR as a :class:`Vocabulary`.

The IR is plain JSON: ``objectTypes`` (entities), ``linkTypes`` (relations),
``actionTypes`` and ``queryTypes``. Both the bare IR and the ``{"ir": ...}`` wrapper
printed by ``model:check --json`` are accepted. The reader checks the shape it relies
on and fails loudly on anything else: a silently empty vocabulary would read as "every
name is unknown".

Only the schema is read. Facts seeded at runtime (instances) are not in the IR, so this
vocabulary is the model's declared words, not its data. Names must follow Open Ontology's own
rules (PascalCase entities, kebab-case relations, actions and queries, ``namespace/name``
fields, every name unique), so a vocabulary slop accepts is one Open Ontology accepts.
"""
from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path

from .interface import Term, TermKind, Vocabulary


class OntologyError(ValueError):
    """The IR is missing, malformed, or declares nothing usable."""


_ENTITY = re.compile(r"^[A-Z][A-Za-z0-9]*$")
_KEBAB = re.compile(r"^[a-z][a-z0-9-]*$")
_FIELD = re.compile(r"^[a-z][a-z0-9_-]*/[a-z][a-z0-9_-]*$")
_SECTIONS = {TermKind.ENTITY: ("objectTypes", "object-type"), TermKind.RELATION: ("linkTypes", "link-type"),
             TermKind.ACTION: ("actionTypes", "action-type"), TermKind.QUERY: ("queryTypes", "query-type")}


class OntologyIR(Vocabulary):
    """A vocabulary read from an Open Ontology IR document."""

    def __init__(self, label: str, terms: Sequence[Term]) -> None:
        self._label = label
        self._terms = tuple(terms)

    @property
    def name(self) -> str:
        return self._label

    def terms(self) -> Sequence[Term]:
        return self._terms

    @classmethod
    def load(cls, path: str | Path) -> "OntologyIR":
        path = Path(path)
        try:
            data = json.loads(path.read_text())
        except OSError as exc:
            raise OntologyError(f"cannot read ontology {path}: {exc.strerror}") from exc
        except json.JSONDecodeError as exc:
            raise OntologyError(f"ontology {path} is not valid JSON: {exc}") from exc
        return cls.parse(data, source=path.name)

    @classmethod
    def parse(cls, data: object, *, source: str = "ontology") -> "OntologyIR":
        if isinstance(data, dict) and "objectTypes" not in data and isinstance(data.get("ir"), dict):
            data = data["ir"]
        if not isinstance(data, dict) or data.get("kind") != "ontology":
            raise OntologyError(f"{source}: not an Open Ontology IR (expected kind 'ontology')")

        def section(key: str) -> list[dict]:
            items = data.get(key, [])
            if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
                raise OntologyError(f"{source}: '{key}' must be a list of objects")
            for item in items:
                if not isinstance(item.get("name"), str) or not item["name"]:
                    raise OntologyError(f"{source}: an entry in '{key}' has no name")
            return items

        def keys(properties: object) -> tuple[str, ...]:
            return tuple(
                str(p.get("key", p.get("name", ""))).lstrip(":")
                for p in properties if isinstance(p, dict)
            ) if isinstance(properties, list) else ()

        terms: list[Term] = []
        for o in section("objectTypes"):
            terms.append(Term(o["name"], TermKind.ENTITY, o.get("description"), keys(o.get("properties"))))
        for r in section("linkTypes"):
            terms.append(Term(r["name"], TermKind.RELATION, r.get("description"),
                              keys(r.get("properties")), (str(r.get("from", "")), str(r.get("to", "")))))
        for a in section("actionTypes"):
            inputs = tuple(str(i.get("name", "")) for i in a.get("input", []) if isinstance(i, dict))
            terms.append(Term(a["name"], TermKind.ACTION, a.get("description"), inputs))
        for q in section("queryTypes"):
            terms.append(Term(q["name"], TermKind.QUERY, q.get("description"), ()))

        if not any(t.kind is TermKind.ENTITY for t in terms):
            raise OntologyError(f"{source}: declares no entities, so there is nothing to compare names against")
        _check_names(terms, source)
        label = f"{data.get('name', source)}@{data.get('version', '?')}"
        return cls(label, terms)

    def as_ir(self) -> dict:
        """The vocabulary as Open Ontology JSON IR. Field types are not known to slop, so each
        field is written as ``json`` (any value), optional and single."""
        model, _, version = self._label.partition("@")
        ir: dict = {"kind": "ontology", "name": model, "version": version or "0.1.0"}
        for kind, (section, item_kind) in _SECTIONS.items():
            ir[section] = [_term_ir(t, item_kind) for t in self._terms if t.kind is kind]
        return ir


def _term_ir(term: Term, item_kind: str) -> dict:
    out: dict = {"kind": item_kind, "name": term.name, "description": term.description}
    if term.kind is TermKind.ACTION:
        out["input"] = [{"name": name} for name in term.fields]
        return out
    if term.kind is TermKind.QUERY:
        return out
    out["properties"] = [{"key": f":{key}", "name": key.split("/", 1)[1], "valueType": {"kind": "json"},
                          "required": False, "unique": False, "cardinality": "one"} for key in term.fields]
    if term.ends is not None:
        out["from"], out["to"] = term.ends
    return out


def _check_names(terms: Sequence[Term], source: str) -> None:
    """Raise unless every name follows Open Ontology's rules and is unique."""
    seen: set[str] = set()
    for term in terms:
        pattern = _ENTITY if term.kind is TermKind.ENTITY else _KEBAB
        if not pattern.match(term.name):
            raise OntologyError(f"{source}: {term.kind.value} name {term.name!r} does not follow Open Ontology's "
                                f"naming rule ({pattern.pattern})")
        if term.name in seen:
            raise OntologyError(f"{source}: the name {term.name!r} is declared more than once")
        seen.add(term.name)
        if term.kind in (TermKind.ENTITY, TermKind.RELATION):
            for key in term.fields:
                if not _FIELD.match(key):
                    raise OntologyError(f"{source}: field {key!r} of {term.name} is not 'namespace/name' ({_FIELD.pattern})")

