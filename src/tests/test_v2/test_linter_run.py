"""End-to-end tests for ``Linter.run()`` against a tiny corpus."""
from __future__ import annotations

from pathlib import Path

from slop.linter.linter import Linter
from slop.linter.rule import Rule
from slop.config import Config


def _config(root: Path) -> Config:
    """Minimal Config — enabled rules, no waivers."""
    return Config(
        root=str(root),
        languages=["python"],
        exclude=[],
        waivers=[],
        rules={},  # defaults applied by rule_config
    )


class TestLinterRun:
    def test_run_returns_result_with_metadata(self, tiny_corpus: Path):
        cfg = _config(tiny_corpus)
        linter = Linter(cfg)
        result = linter.run()
        assert result.root == str(tiny_corpus.resolve())
        assert "python" in result.languages

    def test_run_populates_rule_results(self, tiny_corpus: Path):
        cfg = _config(tiny_corpus)
        result = Linter(cfg).run()
        # Every enabled rule produces a RuleResult.
        assert len(result.rule_results) > 0

    def test_run_aggregate_counts_non_negative(self, tiny_corpus: Path):
        cfg = _config(tiny_corpus)
        result = Linter(cfg).run()
        assert result.slop_count >= 0
        assert result.advisory_count >= 0
        assert result.waived_count >= 0


def _branchy_body(indent: str, n: int = 11) -> str:
    """A body with ``n`` if-statements → CCN = n + 1."""
    return "".join(f"{indent}if x == {i}:\n{indent}    return {i}\n" for i in range(n))


class TestComplexityFiresThroughLinter:
    """Regression guard for the config-keying bug: the complexity.* rules
    have category != name, so a category-keyed config lookup silently
    fed them empty thresholds and they checked nothing. These tests drive
    the rule through ``Linter.run()`` (the path that hid the bug — the
    per-rule unit tests call ``run()`` directly and bypass config wiring).
    """

    def _corpus(self, tmp_path: Path) -> Path:
        # Function with CCN 12 (> 10) and a class whose WMC is 4 * 12 = 48 (> 40).
        func = "def branchy(x):\n" + _branchy_body("    ") + "    return -1\n"
        methods = "".join(
            f"    def m{m}(self, x):\n" + _branchy_body("        ") + "        return -1\n"
            for m in range(4)
        )
        (tmp_path / "fat.py").write_text(func + "\n\nclass Fat:\n" + methods)
        return tmp_path

    def _config(self, root: Path) -> Config:
        return Config(
            root=str(root),
            languages=["python"],
            exclude=[],
            waivers=[],
            rules={
                "complexity.cyclomatic": Rule(
                    enabled=True,
                    severity="error",
                    params={"thresholds": {"function": 10, "class": 40}},
                ),
            },
        )

    def test_cyclomatic_fires_at_both_scopes(self, tmp_path: Path):
        root = self._corpus(tmp_path)
        result = Linter(self._config(root)).run()
        rr = result.rule_results["complexity.cyclomatic"]
        assert rr.status == "fail", f"expected violations, got {rr.summary}"
        scopes = {v.scope for v in rr.violations}
        assert "function" in scopes, f"no function-scope finding: {scopes}"
        assert "class" in scopes, f"no class-scope (WMC) finding: {scopes}"

    def test_thresholds_actually_consumed(self, tmp_path: Path):
        """The configured thresholds must reach the rule — proven by the
        summary reporting a non-zero checked count (the empty-config no-op
        reported 0 functions/0 classes checked)."""
        root = self._corpus(tmp_path)
        result = Linter(self._config(root)).run()
        summary = result.rule_results["complexity.cyclomatic"].summary
        assert summary.get("functions_checked", 0) > 0
        assert summary.get("classes_checked", 0) > 0
