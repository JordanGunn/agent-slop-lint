"""Config: which files slop reads, and which rules run with which options.

A config file (``.slop.toml``, or ``[tool.slop]`` in ``pyproject.toml``) has two keys:

    exclude = ["tests/**"]

    [rules.cyclomatic-complexity]
    limit = 12

``exclude`` lists globs of files never read. A ``[rules.<name>]`` table sets ``enabled``
and the options the rule declares (every limit rule declares ``limit``). Nothing else is
accepted, and nothing accepted is ignored: an unknown key, an unknown rule, an option the
rule does not declare, or an option of the wrong type is an error. That is what makes "no
violations" mean the rules ran as configured, not that a misspelt key switched one off.

``config`` does not import ``rule``: it reads rule metadata (``name``, ``default_config()``)
by duck typing, so there is no import cycle.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, replace
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

_CONFIG_KEYS = frozenset({"exclude", "rules"})


@dataclass(frozen=True)
class RuleConfig:
    """One rule's settings: whether it runs, and its options (``limit``, ...)."""

    name: str
    enabled: bool = True
    options: dict[str, Any] = field(default_factory=dict)

    def option(self, key: str) -> Any:
        return self.options[key]


@dataclass(frozen=True)
class AnalysisConfig:
    rules: dict[str, RuleConfig]
    #: Glob patterns of files never read, matched against the path relative to ``anchor``
    #: (the directory holding the config file). ``*`` matches across ``/``, so ``tests/**``
    #: covers everything beneath ``tests/``.
    exclude: tuple[str, ...] = ()
    anchor: Path | None = None

    def for_rule(self, name: str) -> RuleConfig | None:
        return self.rules.get(name)

    def excludes(self, path: Path) -> bool:
        if not self.exclude or self.anchor is None:
            return False
        try:
            relative = path.resolve().relative_to(self.anchor).as_posix()
        except ValueError:
            return False
        return any(fnmatchcase(relative, pattern) for pattern in self.exclude)

    @classmethod
    def defaults(cls, rule_types: Any) -> AnalysisConfig:
        return cls({rt.name: rt.default_config() for rt in rule_types})

    @classmethod
    def load(cls, root: Path, rule_types: Any) -> AnalysisConfig:
        """Defaults, with the discovered config (found by walking up from ``root``) on top."""
        base = {rt.name: rt.default_config() for rt in rule_types}
        doc, anchor = _discover(Path(root))
        unknown = sorted(set(doc) - _CONFIG_KEYS)
        if unknown:
            raise ValueError(f"config has unknown key(s) {unknown}; slop reads {sorted(_CONFIG_KEYS)}")
        patterns = doc.get("exclude", [])
        if not isinstance(patterns, list) or not all(isinstance(p, str) for p in patterns):
            raise ValueError("config 'exclude' must be a list of glob strings")
        rules = dict(base)
        for name, table in doc.get("rules", {}).items():
            if name not in base:
                raise ValueError(f"config configures unknown rule '{name}'; see `slop rules`")
            rules[name] = _apply(base[name], table)
        return cls(rules, exclude=tuple(patterns), anchor=anchor)


def _apply(base: RuleConfig, table: Any) -> RuleConfig:
    if not isinstance(table, dict):
        raise ValueError(f"rule '{base.name}': expected a table of options")
    declared = set(base.options) | {"enabled"}
    unknown = sorted(set(table) - declared)
    if unknown:
        raise ValueError(f"rule '{base.name}': unknown option(s) {unknown}; it takes {sorted(declared)}")
    enabled = table.get("enabled", base.enabled)
    if not isinstance(enabled, bool):
        raise ValueError(f"rule '{base.name}': 'enabled' must be true or false")
    options = dict(base.options)
    for key in set(table) - {"enabled"}:
        if not _same_kind(base.options[key], table[key]):
            raise ValueError(
                f"rule '{base.name}': option '{key}' must be of type "
                f"{type(base.options[key]).__name__}, got {table[key]!r}")
        options[key] = table[key]
    return replace(base, enabled=enabled, options=options)


def _same_kind(default: Any, value: Any) -> bool:
    """An int option takes an int, a float option takes any number, a bool or a string takes
    its own kind (a bool is not a number)."""
    if isinstance(default, bool) or isinstance(value, bool):
        return isinstance(default, bool) and isinstance(value, bool)
    if isinstance(default, int):
        return isinstance(value, int)
    if isinstance(default, float):
        return isinstance(value, (int, float))
    return isinstance(value, type(default))


def _discover(start: Path) -> tuple[dict[str, Any], Path | None]:
    """Walk up from ``start`` for the nearest ``.slop.toml`` or a ``pyproject.toml`` with a
    ``[tool.slop]`` table; return its table and the directory it was found in, or
    ``({}, None)``."""
    start = start.resolve()
    for directory in [start, *start.parents]:
        slop = directory / ".slop.toml"
        if slop.is_file():
            return _read(slop), directory
        pyproject = directory / "pyproject.toml"
        if pyproject.is_file():
            table = _read(pyproject).get("tool", {}).get("slop")
            if table is not None:
                return table, directory
    return {}, None


def _read(path: Path) -> dict[str, Any]:
    with open(path, "rb") as f:
        return tomllib.load(f)
