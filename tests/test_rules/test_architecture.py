"""Tests for slop packages rule (Robert C. Martin D')."""

from __future__ import annotations

from pathlib import Path

from slop.models import RuleConfig, SlopConfig
from slop.rules.architecture import run_distance


def test_packages_pass_when_clean(tmp_path: Path):
    # A single Python file — no package structure to analyze meaningfully
    (tmp_path / "main.py").write_text("def main():\n    pass\n")
    rc = RuleConfig(enabled=True, severity="warning", params={
        "max_distance": 0.7, "fail_on_zone": ["pain"], "languages": ["python"],
    })
    result = run_distance(tmp_path, rc, SlopConfig(root=str(tmp_path)))
    # Should either pass or skip (single file is unlikely to trigger)
    assert result.status in ("pass", "skip")


def test_packages_skip_when_no_supported_languages(tmp_path: Path):
    (tmp_path / "main.ts").write_text("export function main() {}\n")
    rc = RuleConfig(enabled=True, severity="warning", params={
        "max_distance": 0.7, "fail_on_zone": ["pain"], "languages": ["typescript"],
    })
    result = run_distance(tmp_path, rc, SlopConfig(root=str(tmp_path), languages=["typescript"]))
    # robert only supports go and python — should skip for typescript
    assert result.status == "skip"
