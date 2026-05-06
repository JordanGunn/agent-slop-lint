"""Tests for the composition.* rule suite.

Two rules:

- ``composition.affix_polymorphism`` — token-Levenshtein + FCA
- ``composition.first_parameter_drift`` — first-parameter clustering
"""
from __future__ import annotations

from pathlib import Path

from slop.models import RuleConfig, SlopConfig
from slop.rules.composition import (
    run_affix_polymorphism,
    run_first_parameter_drift,
)


def _slop_config() -> SlopConfig:
    return SlopConfig(rules={}, languages=["python"])


def _rule_config(**overrides) -> RuleConfig:
    return RuleConfig(enabled=True, severity="warning", params=overrides)


# ---------------------------------------------------------------------------
# composition.affix_polymorphism
# ---------------------------------------------------------------------------


_AFFIX_FIXTURE = '''\
def _python_extract(node, content): pass
def _java_extract(node, content): pass
def _csharp_extract(node, content): pass
def _javascript_extract(node, content): pass
def _typescript_extract(node, content): pass
def _python_walk(tree, content): pass
def _java_walk(tree, content): pass
def _csharp_walk(tree, content): pass
def _python_collect(node): pass
def _java_collect(node): pass
'''


def test_affix_polymorphism_detects_language_alphabet(tmp_path: Path):
    (tmp_path / "fixture.py").write_text(_AFFIX_FIXTURE)
    result = run_affix_polymorphism(tmp_path, _rule_config(), _slop_config())
    assert result.status == "fail", result.summary
    assert result.summary["clusters_detected"] >= 1
    # Inheritance edges expected: csharp ⊃ javascript? java ⊃ csharp?
    # The exact pairs depend on the alphabet overlap; just confirm
    # the kernel surfaced *some* concept candidates.
    assert result.summary["concepts_detected"] >= 1


def test_affix_polymorphism_quiet_on_unrelated_functions(tmp_path: Path):
    (tmp_path / "f.py").write_text(
        "def add(a, b): return a + b\n"
        "def parse_input(text): return text.split()\n"
        "def render_output(result): print(result)\n"
    )
    result = run_affix_polymorphism(tmp_path, _rule_config(), _slop_config())
    assert result.status == "pass"
    assert not result.violations


def test_affix_polymorphism_min_alphabet_threshold(tmp_path: Path):
    """Two-value alphabet doesn't qualify with default min_alphabet=3."""
    (tmp_path / "small.py").write_text(
        "def _python_extract(node): pass\n"
        "def _java_extract(node): pass\n"
    )
    result = run_affix_polymorphism(tmp_path, _rule_config(), _slop_config())
    assert result.summary["clusters_detected"] == 0


def test_affix_polymorphism_lowered_threshold_finds_pair(tmp_path: Path):
    """min_alphabet=2 surfaces the small cluster."""
    (tmp_path / "small.py").write_text(
        "def _python_extract(node): pass\n"
        "def _java_extract(node): pass\n"
        "def _python_walk(node): pass\n"
        "def _java_walk(node): pass\n"
    )
    result = run_affix_polymorphism(
        tmp_path, _rule_config(min_alphabet=2), _slop_config(),
    )
    assert result.summary["clusters_detected"] >= 1


def test_affix_polymorphism_violation_metadata(tmp_path: Path):
    (tmp_path / "f.py").write_text(_AFFIX_FIXTURE)
    result = run_affix_polymorphism(tmp_path, _rule_config(), _slop_config())
    if result.violations:
        v = result.violations[0]
        assert v.rule == "composition.affix_polymorphism"
        assert "kind" in v.metadata
        assert v.metadata["kind"] in ("inheritance_pair", "concept")


# ---------------------------------------------------------------------------
# composition.first_parameter_drift
# ---------------------------------------------------------------------------


_FPDRIFT_FIXTURE = '''\
def render(canvas):
    canvas.draw()

def transform(canvas, matrix):
    return canvas.with_(matrix)

def serialize(canvas) -> str:
    return canvas.to_json()

def add(a, b):
    return a + b

def fetch(url):
    return url
'''


def test_first_parameter_drift_detects_strong_cluster(tmp_path: Path):
    (tmp_path / "f.py").write_text(_FPDRIFT_FIXTURE)
    result = run_first_parameter_drift(tmp_path, _rule_config(), _slop_config())
    assert result.status == "fail"
    assert result.summary["strong_clusters"] >= 1
    flagged = {v.symbol for v in result.violations}
    assert "canvas" in flagged


def test_first_parameter_drift_skips_self_and_cls(tmp_path: Path):
    (tmp_path / "f.py").write_text(
        "class Foo:\n"
        "    def a(self): pass\n"
        "    def b(self): pass\n"
        "    def c(self): pass\n"
        "    def d(self): pass\n"
    )
    result = run_first_parameter_drift(tmp_path, _rule_config(), _slop_config())
    flagged = {v.symbol for v in result.violations}
    # `self` is exempt, so no violation
    assert "self" not in flagged


def test_first_parameter_drift_classifies_node_as_false_positive(tmp_path: Path):
    """A bunch of functions taking `node` should be classified as
    false-positive (third-party AST library type)."""
    (tmp_path / "f.py").write_text(
        "def a(node): pass\n"
        "def b(node): pass\n"
        "def c(node): pass\n"
    )
    result = run_first_parameter_drift(tmp_path, _rule_config(), _slop_config())
    # No violations because false-positive verdicts don't generate violations
    flagged = {v.symbol for v in result.violations}
    assert "node" not in flagged
    assert result.summary["false_positive_clusters"] >= 1


def test_first_parameter_drift_classifies_root_as_weak(tmp_path: Path):
    """Functions taking `root: Path` are infrastructure, not domain."""
    (tmp_path / "f.py").write_text(
        "from pathlib import Path\n"
        "def x(root: Path): pass\n"
        "def y(root: Path): pass\n"
        "def z(root: Path): pass\n"
    )
    result = run_first_parameter_drift(tmp_path, _rule_config(), _slop_config())
    flagged = {v.symbol for v in result.violations}
    assert "root" not in flagged  # weak — no violation
    assert result.summary["weak_clusters"] >= 1


def test_first_parameter_drift_min_cluster_threshold(tmp_path: Path):
    (tmp_path / "f.py").write_text(
        "def a(canvas): pass\n"
        "def b(canvas): pass\n"  # only 2 — under default threshold of 3
    )
    result = run_first_parameter_drift(tmp_path, _rule_config(), _slop_config())
    assert result.summary["clusters_detected"] == 0


def test_first_parameter_drift_skips_single_char_params(tmp_path: Path):
    """Single-char parameters (i, x, n) are loop vars / math, not domain."""
    (tmp_path / "f.py").write_text(
        "def a(i): pass\n"
        "def b(i): pass\n"
        "def c(i): pass\n"
        "def d(i): pass\n"
    )
    result = run_first_parameter_drift(tmp_path, _rule_config(), _slop_config())
    flagged = {v.symbol for v in result.violations}
    assert "i" not in flagged


def test_first_parameter_drift_custom_exempt_names(tmp_path: Path):
    (tmp_path / "f.py").write_text(
        "def a(canvas): pass\n"
        "def b(canvas): pass\n"
        "def c(canvas): pass\n"
    )
    result = run_first_parameter_drift(
        tmp_path,
        _rule_config(exempt_names=["self", "cls", "canvas"]),
        _slop_config(),
    )
    flagged = {v.symbol for v in result.violations}
    assert "canvas" not in flagged  # exempt
