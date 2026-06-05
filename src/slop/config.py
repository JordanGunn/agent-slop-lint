"""Analysis config — per-rule enable + per-altitude thresholds.

Config holds **battery/verdict thresholds keyed by altitude**, never algorithm
primitives (those are module constants on the view) — see DESIGN.md "Config
Model". Thresholds are validated at load against each rule's *declared*
altitudes: a threshold key the rule does not declare is a **load error**, not a
silent drop. This is the structural cure for the legacy "config keyed wrong, rule
silently checks nothing" failure.

``config`` intentionally does not import ``rule`` — it consumes rule metadata
(``name``, ``altitudes``, ``default_config()``) by duck typing, so there is no
import cycle with the rule layer. ``AnalysisConfig`` is owned by the ``Corpus``
(the analysis boundary); rules read their slice through ``for_rule``.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from .scope.identity import ScopeKind
from .finding import Severity

_SEVERITY_BY_LABEL = {s.label(): s for s in Severity}


@dataclass(frozen=True)
class RuleConfig:
    """The config slice handed to one rule's ``check``.

    ``thresholds`` is keyed by altitude *label* (``ScopeKind.value``);
    ``params`` carries noise floors / significance gates (legitimately
    configurable even for observations — they govern output volume, not the
    claim).
    """

    name: str
    enabled: bool = True
    severity: Severity = Severity.WARNING
    thresholds: dict[str, float] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)

    def threshold_for(self, kind: ScopeKind) -> float | None:
        return self.thresholds.get(kind.value)

    def param(self, key: str, default: Any = None) -> Any:
        return self.params.get(key, default)


# Exemptions are scope-keyed name lists: a finding is suppressed when the unit it
# judges (its component) is named in the ignore list for that scope. Keys are the
# four nameable scopes; an unknown key is a load error (the legacy "any" footgun).
_IGNORE_KEY = {
    ScopeKind.CALLABLE: "functions",
    ScopeKind.CLASS: "classes",
    ScopeKind.MODULE: "modules",
    ScopeKind.PACKAGE: "packages",
}
_IGNORE_SCOPES = frozenset(_IGNORE_KEY.values())


@dataclass(frozen=True)
class AnalysisConfig:
    rules: dict[str, RuleConfig]
    ignore: dict[str, frozenset[str]] = field(default_factory=dict)

    def for_rule(self, name: str) -> RuleConfig | None:
        return self.rules.get(name)

    def is_ignored(self, component_id: Any) -> bool:
        """True if ``component_id`` (a finding's judged unit) is exempted — its
        qualname (or leaf) is in the ignore list for its scope kind."""
        key = _IGNORE_KEY.get(component_id.kind)
        if key is None:
            return False
        names = self.ignore.get(key, frozenset())
        return component_id.qualname in names or component_id.qualname.split(".")[-1] in names

    @classmethod
    def defaults(cls, rule_types: Any) -> "AnalysisConfig":
        rule_types = list(rule_types)
        merged = {rt.name: rt.default_config() for rt in rule_types}
        for rt in rule_types:
            _validate_threshold_keys(rt.name, merged[rt.name].thresholds, {k.value for k in rt.altitudes})
        return cls(merged)

    @classmethod
    def load(cls, root: Path, rule_types: Any) -> "AnalysisConfig":
        """Defaults, with discovered config (``.slop.toml`` or ``pyproject[tool.slop]``,
        found by walking up from ``root``) merged on top: ``[rules]`` overrides
        validated against each rule's declared altitudes, plus scope-keyed ``[ignore]``."""
        rule_types = list(rule_types)
        base = {rt.name: rt.default_config() for rt in rule_types}
        altitudes = {rt.name: {k.value for k in rt.altitudes} for rt in rule_types}
        doc = _discover(Path(root))
        overrides = doc.get("rules", {})
        merged = dict(base)
        for name, ov in overrides.items():
            if name not in base:
                raise ValueError(f"config configures unknown rule '{name}'")
            merged[name] = _apply_override(base[name], ov, altitudes[name])
        for name, rc in merged.items():
            _validate_threshold_keys(name, rc.thresholds, altitudes[name])
        ignore = _parse_ignore(doc.get("ignore", {}))
        return cls(merged, ignore=ignore)


def _apply_override(base: RuleConfig, ov: dict[str, Any], allowed: set[str]) -> RuleConfig:
    enabled = bool(ov.get("enabled", base.enabled))
    severity = base.severity
    if "severity" in ov:
        label = str(ov["severity"]).lower()
        if label not in _SEVERITY_BY_LABEL:
            raise ValueError(f"rule '{base.name}': unknown severity '{ov['severity']}'")
        severity = _SEVERITY_BY_LABEL[label]
    thresholds = dict(base.thresholds)
    if "thresholds" in ov:
        thresholds.update({str(k): float(v) for k, v in ov["thresholds"].items()})
    params = dict(base.params)
    for k, v in ov.items():
        if k not in ("enabled", "severity", "thresholds"):
            params[k] = v
    _validate_threshold_keys(base.name, thresholds, allowed)
    return replace(base, enabled=enabled, severity=severity, thresholds=thresholds, params=params)


def _validate_threshold_keys(name: str, thresholds: dict[str, float], allowed: set[str]) -> None:
    for key in thresholds:
        if key not in allowed:
            raise ValueError(
                f"rule '{name}': threshold altitude '{key}' is not a declared altitude "
                f"{sorted(allowed)} — a threshold the rule can never apply"
            )


def _parse_ignore(raw: Any) -> dict[str, frozenset[str]]:
    """Validate + normalise the scope-keyed ignore map. Unknown scope keys raise
    (the legacy ``ignore.any`` footgun read as 'clean')."""
    if not raw:
        return {}
    out: dict[str, frozenset[str]] = {}
    for key, names in raw.items():
        if key not in _IGNORE_SCOPES:
            raise ValueError(
                f"[ignore] has unknown scope '{key}'; expected one of {sorted(_IGNORE_SCOPES)}")
        out[key] = frozenset(str(n) for n in names)
    return out


def _discover(start: Path) -> dict[str, Any]:
    """Walk up from ``start`` for the nearest ``.slop.toml`` or a ``pyproject.toml``
    carrying ``[tool.slop]``. A pyproject without ``[tool.slop]`` is skipped (so a
    sub-project pyproject does not mask a repo-root ``.slop.toml``)."""
    start = start.resolve()
    for cur in [start, *start.parents]:
        slop = cur / ".slop.toml"
        if slop.is_file():
            return _read_toml(slop)
        pyproject = cur / "pyproject.toml"
        if pyproject.is_file():
            tool_slop = _read_toml(pyproject).get("tool", {}).get("slop")
            if tool_slop is not None:
                return tool_slop
    return {}


def _read_toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)
