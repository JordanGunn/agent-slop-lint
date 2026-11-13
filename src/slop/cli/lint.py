"""The lint commands: ``lint``, ``check`` and ``rules``. They exit 0 with no violations, 1 with
any, 2 on error."""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

from .. import ontology
from . import resolve
from ..config import AnalysisConfig
from ..dispatch import Dispatcher, Report
from ..infer.apply.settle import settle
from ..infer.contract import Status, dump
from ..infer.ledger.jsonl import JsonlLedger
from ..infer.source.interface import Analysis
from ..rules import RULE_REGISTRY
from ..scope import scan_corpus
from .. import violation
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
    try:
        vocabulary = resolve.vocabulary(root)
    except ontology.OntologyError as exc:
        print(f"slop: error: {exc}", file=sys.stderr)
        return None
    corpus = scan_corpus(root, config, vocabulary=vocabulary)
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
        print(json.dumps(_annotated(report, settlement, analysis), indent=2))
    else:
        print(_human(report, settlement))
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


def _annotated(report: Report, settlement, analysis: Analysis) -> dict:
    """The report as JSON, with the absolute ``project_root`` every id and residue ``path`` is
    relative to; each finding's ``id``, and its ``residue`` where it can be put to inference;
    and the ``agglomerations`` its findings form (``slop.agglomeration``)."""
    doc = report.as_dict()
    root = analysis.root
    doc["project_root"] = str(root.resolve())
    for key in ("violations", "warnings"):
        for entry, finding in zip(doc[key], getattr(report, key)):
            entry["id"] = finding.id(root)
            item = settlement.residue.get(finding.position)
            if item is not None:
                entry["residue"] = dump(item)
    doc["agglomerations"] = [{"id": g.id, "topology": g.topology.value, "lead": violation.scope_json(g.lead),
                              "units": [violation.scope_json(u) for u in g.units], "findings": [f.id(root) for f in g.findings],
                              **({"residue": dump(settlement.groups[g.id])} if g.id in settlement.groups else {})}
                             for g in settlement.agglomerations]
    for group in doc["agglomerations"]:
        for scope in (group["lead"], *group["units"]):
            scope["path"] = report.relative(scope["path"])
    return doc


def _human(report: Report, settlement) -> str:
    """One ``path:line:column: rule message`` line per violation, the shape editors and
    other tools already parse; then one ``WARN`` line per subjective finding, tagged with where
    its ruling stands; then a summary that says how many findings wait for a ruling."""
    def at(v) -> str:
        return f"{report.relative_path(v) or '<corpus>'}:{v.line}:{v.column}"

    tags = {position: _tag(item, settlement.rulings.get(item.id)) for position, item in settlement.residue.items()}
    lines = [f"{at(v)}: {v.rule} {v.message}" for v in report.violations]
    lines += [f"{at(v)}: WARN {v.rule} {v.message}{tags.get(v.position, '')}" for v in report.warnings]
    errors, warnings = len(report.violations), len(report.warnings)
    head = f"Found {errors} violation{'s' if errors != 1 else ''}" if errors else "No violations"
    tail = f" and {warnings} warning{'s' if warnings != 1 else ''}" if warnings else ""
    statuses = [settlement.residue[v.position].status for v in report.warnings if v.position in settlement.residue]
    unruled, stale = statuses.count(Status.NONE), statuses.count(Status.STALE)
    waiting = (f" {unruled + stale} {'waits' if unruled + stale == 1 else 'wait'} for a ruling ({unruled} never ruled, {stale} stale): see "
               "`slop infer instructions`.") if unruled + stale else ""
    lines.append(f"{head}{tail}.{waiting}")
    return "\n".join(lines)


def _tag(item, ruling) -> str:
    """Where a warning's ruling stands, as a suffix: never ruled, stale and why, or deferred."""
    if item.status is Status.NONE:
        return " [not ruled]"
    if item.status is Status.STALE:
        cause = "rubric" if ruling.rubric_version != item.rubric.version else "code"
        return f" [stale: the {cause} changed since it was ruled {ruling.verdict.outcome.value}]"
    if item.status is Status.DEFER:
        return f" [deferred: {ruling.verdict.reason}]"
    return ""
