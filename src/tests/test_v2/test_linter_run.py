"""End-to-end tests for ``Linter.run()`` against a tiny corpus."""
from __future__ import annotations

from pathlib import Path

from slop.linter.linter import Linter
from slop.linter.rule_config import RuleConfig
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
