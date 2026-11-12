"""``.slop/ontology.json``: the vocabulary as a JSON document with SKOS property names.

    {"version": 1, "scheme": "laszy", "terms": [
      {"prefLabel": "Copc", "definition": "A cloud optimised point cloud: a Laz variant ...",
       "altLabel": [], "hiddenLabel": [], "broader": ["Laz"], "related": []}]}

Only ``prefLabel`` is required in a term. Reading is strict: an unknown key or a wrongly typed
value is an error, so a typo never silently drops a definition.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model import Scheme, Term

VERSION = 1
_PREF = "prefLabel"
_LISTS = {"altLabel": "alt_labels", "hiddenLabel": "hidden_labels", "broader": "broader", "related": "related"}
_KEYS = {_PREF, "definition", *_LISTS}


class OntologyError(ValueError):
    """The vocabulary file is missing, unreadable or malformed."""


def load(path: Path) -> Scheme:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise OntologyError(f"no vocabulary at {path}; run `slop ontology draft`") from None
    except (OSError, json.JSONDecodeError) as exc:
        raise OntologyError(f"cannot read {path}: {exc}") from None
    return parse(document, str(path))


def parse(document: Any, where: str = "ontology") -> Scheme:
    if not isinstance(document, dict) or set(document) != {"version", "scheme", "terms"}:
        raise OntologyError(f"{where}: expected exactly the keys version, scheme, terms")
    if document["version"] != VERSION:
        raise OntologyError(f"{where}: version {document['version']!r} is not {VERSION}")
    if not isinstance(document["scheme"], str) or not isinstance(document["terms"], list):
        raise OntologyError(f"{where}: scheme must be a string and terms a list")
    return Scheme(document["scheme"], (_term(t, f"{where}: term {i}") for i, t in enumerate(document["terms"])))


def save(scheme: Scheme, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dump(scheme), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def dump(scheme: Scheme) -> dict[str, Any]:
    return {"version": VERSION, "scheme": scheme.name, "terms": [_entry(t) for t in scheme.terms]}


def _entry(term: Term) -> dict[str, Any]:
    entry: dict[str, Any] = {_PREF: term.pref_label, "definition": term.definition}
    entry.update({key: list(getattr(term, attr)) for key, attr in _LISTS.items()})
    return entry


def _term(raw: Any, where: str) -> Term:
    if not isinstance(raw, dict) or _PREF not in raw:
        raise OntologyError(f"{where}: a term is an object with a prefLabel")
    unknown = set(raw) - _KEYS
    if unknown:
        raise OntologyError(f"{where}: unknown key(s) {sorted(unknown)}")
    if not isinstance(raw[_PREF], str) or not raw[_PREF]:
        raise OntologyError(f"{where}: prefLabel must be a non-empty string")
    definition = raw.get("definition")
    if definition is not None and not isinstance(definition, str):
        raise OntologyError(f"{where}: definition must be a string or null")
    return Term(pref_label=raw[_PREF], definition=definition, **_lists(raw, where))


def _lists(raw: dict, where: str) -> dict[str, tuple[str, ...]]:
    """The term's label and link lists, each a list of non-empty strings."""
    lists = {}
    for key, attr in _LISTS.items():
        value = raw.get(key, [])
        if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
            raise OntologyError(f"{where}: {key} must be a list of non-empty strings")
        lists[attr] = tuple(value)
    return lists
