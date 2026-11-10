"""Config: which files slop reads, and per rule whether it runs and where its limits sit.

A config file (``.slop.toml``, or ``[tool.slop]`` in ``pyproject.toml``) has three keys:
``exclude`` and ``languages`` choose what is read, and ``[rules."<name>"]`` tunes a rule
(``enabled``, ``thresholds``, ``params``). Nothing else is accepted, and nothing accepted
is ignored: a threshold keyed to an altitude the rule does not declare, a param the rule
never reads, or a key slop does not know is a load error. That is what makes "no
violations" mean the rules ran as configured, not that a misspelt key switched them off.

``config`` does not import ``rule``: it consumes rule metadata (``name``, ``altitudes``,
``default_config()``) by duck typing, so there is no import cycle with the rule layer.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, replace
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

from .scope.identity import ScopeKind

_CONFIG_KEYS = frozenset({"exclude", "languages", "rules"})


@dataclass(frozen=True)
class RuleConfig:
    """The config slice handed to one rule's ``check``.

    ``thresholds`` is keyed by altitude *label* (``ScopeKind.value``); ``params`` holds a
    rule's other settings (a window, a minimum size).
    """

    name: str
    enabled: bool = True
    thresholds: dict[str, float] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)

    def threshold_for(self, kind: ScopeKind) -> float | None:
        return self.thresholds.get(kind.value)

    def param(self, key: str, default: Any = None) -> Any:
        return self.params.get(key, default)


@dataclass(frozen=True)
class Exclusion:
    """Files the corpus must not carve: ``fnmatch`` globs over POSIX paths relative to
    ``anchor``, the directory holding the config. ``*`` crosses ``/`` (so ``tests/**``
    covers everything beneath ``tests/``), and a leading ``**/`` also matches the top
    level (``**/vendor/**`` covers ``vendor/x.py``). A file outside ``anchor`` is never
    excluded."""

    patterns: tuple[str, ...] = ()
    anchor: Path | None = None

    def excludes(self, path: Path) -> bool:
        if not self.patterns or self.anchor is None:
            return False
        try:
            rel = path.resolve().relative_to(self.anchor).as_posix()
        except ValueError:
            return False
        return any(
            fnmatchcase(rel, pat) or (pat.startswith("**/") and fnmatchcase(rel, pat[3:]))
            for pat in self.patterns
        )


@dataclass(frozen=True)
class AnalysisConfig:
    rules: dict[str, RuleConfig]
    exclusion: Exclusion = field(default_factory=Exclusion)
    #: Language ids to carve (``python``, ``typescript`` ...); empty means all of them.
    languages: frozenset[str] = frozenset()

    def for_rule(self, name: str) -> RuleConfig | None:
        return self.rules.get(name)

    @classmethod
    def defaults(cls, rule_types: Any) -> AnalysisConfig:
        rule_types = list(rule_types)
        merged = {rt.name: rt.default_config() for rt in rule_types}
        for rt in rule_types:
            _validate_threshold_keys(rt.name, merged[rt.name].thresholds, {k.value for k in rt.altitudes})
        return cls(merged)

    @classmethod
    def scan(cls, root: Path, rule_types: Any) -> AnalysisConfig:
        """Default rules plus the discovered config's scan settings (``exclude``,
        ``languages``), for commands that read the corpus but never check it. ``[rules]``
        is not read, so a config naming a rule slop no longer has cannot block them;
        ``load`` is the strict path for ``lint`` and ``check``."""
        doc, anchor = _discover(Path(root))
        return replace(cls.defaults(rule_types), **_scan_settings(doc, anchor))

    @classmethod
    def load(cls, root: Path, rule_types: Any) -> AnalysisConfig:
        """Defaults, with the discovered config (``.slop.toml`` or ``pyproject[tool.slop]``,
        found by walking up from ``root``) merged on top: ``[rules]`` overrides validated
        against each rule's declared altitudes and params, plus the scan settings."""
        rule_types = list(rule_types)
        base = {rt.name: rt.default_config() for rt in rule_types}
        altitudes = {rt.name: {k.value for k in rt.altitudes} for rt in rule_types}
        doc, anchor = _discover(Path(root))
        unknown = sorted(set(doc) - _CONFIG_KEYS)
        if unknown:
            raise ValueError(
                f"config has unknown key(s) {unknown}; slop reads {sorted(_CONFIG_KEYS)}")
        merged = dict(base)
        for name, ov in doc.get("rules", {}).items():
            if name not in base:
                raise ValueError(f"config configures unknown rule '{name}'")
            merged[name] = _apply_override(base[name], ov, altitudes[name])
        for name, rc in merged.items():
            _validate_threshold_keys(name, rc.thresholds, altitudes[name])
        return cls(merged, **_scan_settings(doc, anchor))


def _parse_exclusion(doc: dict[str, Any], anchor: Path | None) -> Exclusion:
    raw = doc.get("exclude", [])
    if not isinstance(raw, list) or not all(isinstance(p, str) for p in raw):
        raise ValueError("config 'exclude' must be a list of glob strings")
    return Exclusion(tuple(raw), anchor)


def _parse_languages(doc: dict[str, Any]) -> frozenset[str]:
    """The language ids to carve; empty means every supported language."""
    from .ast import GRAMMARS_BY_ID
    raw = doc.get("languages", [])
    if not isinstance(raw, list) or not all(isinstance(x, str) for x in raw):
        raise ValueError("config 'languages' must be a list of language ids")
    unknown = sorted(set(raw) - set(GRAMMARS_BY_ID))
    if unknown:
        raise ValueError(
            f"config 'languages' names unknown language(s) {unknown}; supported: "
            f"{sorted(GRAMMARS_BY_ID)}")
    return frozenset(raw)


def _scan_settings(doc: dict[str, Any], anchor: Path | None) -> dict[str, Any]:
    """What the config says about which files the corpus carves, for ``AnalysisConfig``."""
    return {"exclusion": _parse_exclusion(doc, anchor), "languages": _parse_languages(doc)}


def _apply_override(base: RuleConfig, ov: dict[str, Any], allowed: set[str]) -> RuleConfig:
    stray = set(ov) - {"enabled", "thresholds", "params"}
    if stray:
        raise ValueError(
            f"rule '{base.name}': unknown key(s) {sorted(stray)}; a rule takes 'enabled', "
            f"'thresholds' and 'params' (params.<name> = ...)")
    enabled = bool(ov.get("enabled", base.enabled))
    thresholds = dict(base.thresholds)
    if "thresholds" in ov:
        thresholds.update({str(k): float(v) for k, v in ov["thresholds"].items()})
    overrides = ov.get("params", {})
    if not isinstance(overrides, dict):
        raise ValueError(f"rule '{base.name}': 'params' must be a table")
    for key in overrides:
        if key not in base.params:
            raise ValueError(
                f"rule '{base.name}': param '{key}' is not a declared param "
                f"{sorted(base.params)}; the rule can never read it")
    params = {**base.params, **overrides}
    _validate_threshold_keys(base.name, thresholds, allowed)
    return replace(base, enabled=enabled, thresholds=thresholds, params=params)


def _validate_threshold_keys(name: str, thresholds: dict[str, float], allowed: set[str]) -> None:
    for key in thresholds:
        if key not in allowed:
            raise ValueError(
                f"rule '{name}': threshold altitude '{key}' is not a declared altitude "
                f"{sorted(allowed)}; the rule can never apply it"
            )


def _discover(start: Path) -> tuple[dict[str, Any], Path | None]:
    """Walk up from ``start`` for the nearest ``.slop.toml`` or a ``pyproject.toml``
    carrying ``[tool.slop]``; return its table and the directory it was found in (the
    anchor for relative paths in it), or ``({}, None)``. A pyproject without
    ``[tool.slop]`` is skipped (so a sub-project pyproject does not mask a repo-root
    ``.slop.toml``)."""
    start = start.resolve()
    for cur in [start, *start.parents]:
        slop = cur / ".slop.toml"
        if slop.is_file():
            return _read_toml(slop), cur
        pyproject = cur / "pyproject.toml"
        if pyproject.is_file():
            tool_slop = _read_toml(pyproject).get("tool", {}).get("slop")
            if tool_slop is not None:
                return tool_slop, cur
    return {}, None


def _read_toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)
