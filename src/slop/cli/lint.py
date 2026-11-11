"""The lint commands: ``lint``, ``check`` and ``rules``. They exit 0 with no violations, 1 with
any, 2 on error."""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

from ..config import AnalysisConfig
from ..dispatch import Dispatcher, Report
from ..infer.apply.settle import settle
from ..infer.contract import dump
from ..infer.ledger.jsonl import JsonlLedger
from ..infer.source.interface import Analysis
from ..rules import RULE_REGISTRY
from ..scope import scan_corpus
from .render import add_output
from .resolve import add_root, has_source, project_root


def register(sub) -> None:
    p_lint = sub.add_parser("lint", help="lint a source root")
    add_root(p_lint)
    add_output(p_lint)
    p_lint.set_defaults(run=lambda a: lint(a.root, a.output))

    p_check = sub.add_parser("check", help="run only the named rules")
    p_check.add_argument("rules", nargs="+", help="rule name(s) to run (see `slop rules`)")
    add_root(p_check)
    add_output(p_check)
    p_check.set_defaults(run=lambda a: check(a.rules, a.root, a.output))

    p_rules = sub.add_parser("rules", help="list the rule registry")
    add_output(p_rules)
    p_rules.set_defaults(run=lambda a: rules(a.output))


def analyse(root: str | Path, selected=None) -> Analysis | None:
    """Scan ``root`` and run every enabled rule, or only ``selected`` (which then run whether or
    not the config has them enabled). None, after printing why, on a missing or source-free root."""
    root = Path(root)
    if not root.exists():
        print(f"slop: error: root path does not exist: {root}", file=sys.stderr)
        return None
    config = AnalysisConfig.load(root, RULE_REGISTRY)
    if selected is not None:
        config = replace(config, rules={
            **config.rules, **{r.name: replace(config.rules[r.name], enabled=True) for r in selected}})
    corpus = scan_corpus(root, config)
    if not has_source(corpus):
        print(f"slop: error: no source files found under {root}", file=sys.stderr)
        return None
    report = Dispatcher(RULE_REGISTRY if selected is None else selected, config).run(corpus)
    return Analysis(root=project_root(root, config), report=report, corpus=corpus)


def lint(root: str | Path, output: str = "human", *, selected=None) -> int:
    """Run every enabled rule, or only ``selected``, then apply the project's inference rulings."""
    analysis = analyse(root, selected)
    if analysis is None:
        return 2
    settlement = settle(analysis, JsonlLedger.at(analysis.root))
    report = settlement.report
    if output == "json":
        print(json.dumps(_with_residue(report.as_dict(), settlement, analysis.root), indent=2))
    else:
        print(_human(report))
    return report.exit_code()


def check(names: list[str], root: str | Path, output: str = "human") -> int:
    """Run only the named rules, even if the config or the default has them off."""
    by_name = {r.name: r for r in RULE_REGISTRY}
    unknown = [n for n in names if n not in by_name]
    if unknown:
        print(f"slop: unknown rule(s) {unknown}. Try `slop rules`.", file=sys.stderr)
        return 2
    return lint(root, output, selected=[by_name[n] for n in names])


def rules(output: str = "human") -> int:
    """List the rule registry: name, whether it is on by default, objective or subjective, altitudes."""
    rows = [(r.name, ",".join(sorted(k.value for k in r.altitudes)),
             r.default_config().enabled, r.subjective, r.description)
            for r in sorted(RULE_REGISTRY, key=lambda x: x.name)]
    if output == "json":
        print(json.dumps([{"name": n, "altitudes": a.split(","), "enabled": on, "subjective": sub,
                           "description": d} for n, a, on, sub, d in rows], indent=2))
        return 0
    width = max((len(n) for n, *_ in rows), default=4)
    print(f"{len(rows)} rules\n")
    for n, a, on, sub, d in rows:
        print(f"  {n:<{width}}  {'on ' if on else 'off'}  {'subjective' if sub else 'objective'}  [{a}]  {d}")
    return 0


def _with_residue(doc: dict, settlement, root: Path) -> dict:
    """``doc`` with each finding that can be put to inference carrying its ``residue``, and the
    absolute ``project_root`` that every residue ``path`` is relative to."""
    doc["project_root"] = str(root.resolve())
    for key in ("violations", "warnings"):
        for entry, finding in zip(doc[key], getattr(settlement.report, key)):
            item = settlement.residue.get(finding.position)
            if item is not None:
                entry["residue"] = dump(item)
    return doc


def _human(report: Report) -> str:
    """One ``path:line:column: rule message`` line per violation, the shape editors and
    other tools already parse; then one ``WARN`` line per subjective finding; then a summary."""
    def at(v) -> str:
        return f"{report.relative_path(v) or '<corpus>'}:{v.line}:{v.column}"

    lines = [f"{at(v)}: {v.rule} {v.message}" for v in report.violations]
    lines += [f"{at(v)}: WARN {v.rule} {v.message}" for v in report.warnings]
    errors, warnings = len(report.violations), len(report.warnings)
    head = f"Found {errors} violation{'s' if errors != 1 else ''}" if errors else "No violations"
    tail = f" and {warnings} warning{'s' if warnings != 1 else ''}" if warnings else ""
    lines.append(f"{head}{tail}.")
    return "\n".join(lines)
