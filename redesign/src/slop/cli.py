"""slop CLI — ``slop lint --root <path>``.

Scans a root into a Corpus, runs the rule dispatcher, renders findings (human or
JSON), and returns an exit code: 0 clean / 1 violations (any ERROR finding) /
2 error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import AnalysisConfig
from .dispatch import Dispatcher, Report
from .scope import scan_corpus
from .rules import RULE_REGISTRY


def lint(root: str | Path, output: str = "human") -> int:
    root = Path(root)
    config = AnalysisConfig.load(root, RULE_REGISTRY)
    corpus = scan_corpus(root, config)
    report = Dispatcher(RULE_REGISTRY, config).run(corpus)
    if output == "json":
        print(json.dumps(report.as_dict(), indent=2))
    else:
        print(_human(report))
    return report.exit_code()


def _human(report: Report) -> str:
    lines: list[str] = []
    verdicts = report.verdicts()
    observations = report.observations()

    if verdicts:
        lines.append("VERDICTS")
        for v in sorted(verdicts, key=lambda f: (-int(f.severity), f.rule)):
            lines.append(f"  [{v.severity.label()}] {v.rule}  ·  {v.component.qualname}")
            lines.append(f"      {v.message}")
            lines.append(f"      → {v.action.value}: {v.prescription}")
        lines.append("")

    if observations:
        lines.append("OBSERVATIONS")
        for o in observations:
            lines.append(f"  [info] {o.rule}  ·  {o.component.qualname}")
            lines.append(f"      {o.message}")
        lines.append("")

    if report.zero_visited:
        lines.append(f"note: {len(report.zero_visited)} enabled rule(s) examined 0 components: "
                     f"{', '.join(report.zero_visited)}")
        lines.append("")

    s = report.as_dict()["summary"]
    summary = (f"{s['verdicts']} verdict(s) ({s['errors']} error, {s['warnings']} warning), "
               f"{s['observations']} observation(s) — exit {s['exit_code']}")
    if not report.findings:
        return "clean — no findings\n\n" + summary
    lines.append(summary)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="slop", description="agentic code-quality linter")
    sub = parser.add_subparsers(dest="command", required=True)
    p_lint = sub.add_parser("lint", help="lint a source root")
    p_lint.add_argument("--root", default=".", help="source root to scan (default: cwd)")
    p_lint.add_argument("--output", choices=["human", "json"], default="human")
    args = parser.parse_args(argv)

    if args.command == "lint":
        try:
            return lint(args.root, args.output)
        except Exception as exc:  # noqa: BLE001 — top-level boundary: any failure is exit 2
            print(f"slop: error: {exc}", file=sys.stderr)
            return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
