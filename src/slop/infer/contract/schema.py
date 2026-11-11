"""Schema and strict parsing from one declaration: a frozen dataclass of the contract.

``schema_of`` renders the JSON Schema an agent reads. ``parse`` checks a document against
the same declaration and builds the object. ``dump`` is the inverse. Supported field types
are ``str``, ``int``, ``float``, ``bool``, an ``Enum``, ``tuple[T, ...]``, ``T | None`` and a
nested dataclass. A field may carry ``metadata`` with ``description``, ``min_length``,
``max_length`` or ``const``.
"""
from __future__ import annotations

import dataclasses
import types
from enum import Enum
from typing import Any, Union, get_args, get_origin, get_type_hints

_DIALECT = "https://json-schema.org/draft/2020-12/schema"

#: Field metadata keys, and the JSON Schema keyword each one becomes.
_KEYWORDS = {"description": "description", "min_length": "minLength", "max_length": "maxLength",
             "const": "const"}


def described(description: str, **constraints: Any) -> Any:
    """A dataclass field that carries a description and, optionally, ``min_length``,
    ``max_length`` or ``const``. Both the schema and the parser read them."""
    return dataclasses.field(metadata={"description": description, **constraints})


class ContractError(ValueError):
    """A document does not match the contract. The message names the offending path."""


def schema_of(cls: type) -> dict[str, Any]:
    """The JSON Schema document for ``cls``."""
    return {"$schema": _DIALECT, **_object_schema(cls)}


def parse(cls: type, data: Any) -> Any:
    """Build a ``cls`` from ``data`` or raise ``ContractError``. Unknown fields are errors."""
    return _parse_object(cls, data, "$")


def dump(value: Any) -> Any:
    """The JSON-ready form of a contract object."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: dump(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (tuple, list)):
        return [dump(v) for v in value]
    return value


# ---- schema ---------------------------------------------------------------

def _object_schema(cls: type) -> dict[str, Any]:
    hints = get_type_hints(cls)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for field in dataclasses.fields(cls):
        properties[field.name] = _type_schema(hints[field.name], field.metadata)
        if field.default is dataclasses.MISSING and field.default_factory is dataclasses.MISSING:
            required.append(field.name)
    out: dict[str, Any] = {"title": cls.__name__, "type": "object", "additionalProperties": False,
                           "properties": properties, "required": required}
    if cls.__doc__:
        out["description"] = " ".join(cls.__doc__.split())
    return out


def _type_schema(tp: Any, meta: Any) -> dict[str, Any]:
    out = _bare_schema(tp)
    for key, keyword in _KEYWORDS.items():
        if key in meta:
            out[keyword] = meta[key]
    return out


def _bare_schema(tp: Any) -> dict[str, Any]:
    if _is_optional(tp):
        (inner,) = [a for a in get_args(tp) if a is not type(None)]
        return {"anyOf": [_bare_schema(inner), {"type": "null"}]}
    if get_origin(tp) is tuple:
        return {"type": "array", "items": _bare_schema(get_args(tp)[0])}
    if isinstance(tp, type) and issubclass(tp, Enum):
        return {"enum": [m.value for m in tp]}
    if dataclasses.is_dataclass(tp):
        return _object_schema(tp)
    if tp is bool:
        return {"type": "boolean"}
    if tp is int:
        return {"type": "integer"}
    if tp is float:
        return {"type": "number"}
    if tp is str:
        return {"type": "string"}
    raise TypeError(f"unsupported contract type: {tp!r}")


def _is_optional(tp: Any) -> bool:
    return get_origin(tp) in (Union, types.UnionType) and type(None) in get_args(tp)


# ---- parsing --------------------------------------------------------------

def _parse_object(cls: type, data: Any, path: str) -> Any:
    if not isinstance(data, dict):
        raise ContractError(f"{path}: expected an object, got {_name(data)}")
    hints = get_type_hints(cls)
    fields = {f.name: f for f in dataclasses.fields(cls)}
    for key in data:
        if key not in fields:
            raise ContractError(f"{path}: unknown field '{key}'")
    values: dict[str, Any] = {}
    for name, field in fields.items():
        if name not in data:
            if field.default is dataclasses.MISSING and field.default_factory is dataclasses.MISSING:
                raise ContractError(f"{path}: missing field '{name}'")
            continue
        values[name] = _parse_value(hints[name], data[name], f"{path}.{name}", field.metadata)
    return cls(**values)


def _parse_value(tp: Any, value: Any, path: str, meta: Any) -> Any:
    if _is_optional(tp):
        if value is None:
            return None
        (inner,) = [a for a in get_args(tp) if a is not type(None)]
        return _parse_value(inner, value, path, meta)
    if get_origin(tp) is tuple:
        if not isinstance(value, list):
            raise ContractError(f"{path}: expected an array, got {_name(value)}")
        item = get_args(tp)[0]
        return tuple(_parse_value(item, v, f"{path}[{i}]", {}) for i, v in enumerate(value))
    if isinstance(tp, type) and issubclass(tp, Enum):
        try:
            return tp(value)
        except ValueError:
            allowed = ", ".join(repr(m.value) for m in tp)
            raise ContractError(f"{path}: {value!r} is not one of {allowed}") from None
    if dataclasses.is_dataclass(tp):
        return _parse_object(tp, value, path)
    parsed = _parse_scalar(tp, value, path)
    _check_meta(parsed, path, meta)
    return parsed


def _parse_scalar(tp: Any, value: Any, path: str) -> Any:
    if tp is bool:
        ok = isinstance(value, bool)
    elif tp is int:
        ok = isinstance(value, int) and not isinstance(value, bool)
    elif tp is float:
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
        value = float(value) if ok else value
    elif tp is str:
        ok = isinstance(value, str)
    else:
        raise TypeError(f"unsupported contract type: {tp!r}")
    if not ok:
        raise ContractError(f"{path}: expected {tp.__name__}, got {_name(value)}")
    return value


def _check_meta(value: Any, path: str, meta: Any) -> None:
    if "const" in meta and value != meta["const"]:
        raise ContractError(f"{path}: must be {meta['const']!r}, got {value!r}")
    if isinstance(value, str):
        shortest, longest = meta.get("min_length"), meta.get("max_length")
        if shortest is not None and len(value) < shortest:
            raise ContractError(f"{path}: shorter than {shortest} characters")
        if longest is not None and len(value) > longest:
            raise ContractError(f"{path}: longer than {longest} characters")


def _name(value: Any) -> str:
    return "null" if value is None else type(value).__name__
