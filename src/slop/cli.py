"""slop CLI.

Primitives (read-only views over the layers): ``ast`` / ``tree`` / ``find`` / ``lexicon`` /
``deps`` / ``vocab`` / ``shape``. Lint: ``lint`` / ``check`` / ``rules``. Housekeeping:
``doctor`` / ``init``.

The primitives answer questions and exit 0 whenever they answered (an empty result is an
answer); 2 means the question could not be answered. The lint commands exit 0 with no
violations, 1 with any, 2 on error.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version as _pkg_version
from pathlib import Path

from .config import AnalysisConfig
from .dispatch import Dispatcher, Report
from .scope import scan_corpus
from .scope.identity import ScopeKind
from .rules import RULE_REGISTRY
from .ontology import OntologyIR, compare
from .metrics.structural.view import Structure
from .lexical import coverage as lexical_coverage
from .scope import find as discovery
from .metrics.structural.hotspots import DEFAULT_LAST
from .identity import relative_path as _rel_path
from .infer.apply.route import route
from .infer.apply.settle import settle
from .infer.bundle import prose
from .infer.contract import ContractError, Verdicts, dump, parse, schemas as infer_schemas
from .infer.ledger.jsonl import JsonlLedger
from .infer.source.finding import FindingSource
from .infer.source.interface import Analysis as InferAnalysis
from .layout import CONFIG_FILENAME
from .skill.catalog import SKILLS
from .skill.install import InstallError, install as install_skill
from .scope.find import walk as _walk
from .scope.lexicon import build_declared_lexicon


def _version() -> str:
    """The installed distribution version, or ``unknown`` when running from a source
    tree that was never installed (no dist metadata to read)."""
    try:
        return _pkg_version("agent-slop-lint")
    except PackageNotFoundError:
        return "unknown"


def _resolve_scope(corpus, ident: str, kind: ScopeKind | None = None) -> list:
    """Scopes matching ``ident`` by qualname or by relative file path, optionally of one
    ``kind``. A list, since a bare qualname can repeat (``view`` in two packages,
    overloads) and a package shares its qualname with its ``__init__`` module. Empty if
    none match."""
    root = str(corpus.root)
    # qualname matches any kind; a path identifies a file, so it matches the MODULE only
    # (every callable/class in the file shares that path, but the file *is* the module).
    return [c for c in _walk(corpus)
            if (c.qualname == ident
                or (c.id.kind is ScopeKind.MODULE and _rel_path(c.id, root) == ident))
            and (kind is None or c.id.kind is kind)]


def _select_scope(corpus, ident: str, kind: ScopeKind | None = None):
    """Resolve ``ident`` to a single scope, or print an error and return None: nothing
    matched, or it was ambiguous (in which case each candidate and its kind is listed, and
    ``--scope-kind`` or a path picks one)."""
    matches = _resolve_scope(corpus, ident, kind)
    if not matches:
        print(f"slop: error: no scope with qualname or path '{ident}'", file=sys.stderr)
        return None
    if len(matches) > 1:
        print(f"slop: error: '{ident}' is ambiguous ({len(matches)} matches); "
              "disambiguate with --scope-kind or by path:", file=sys.stderr)
        for m in matches:
            print(f"  {m.id.kind.value:<8} {_rel_path(m.id, str(corpus.root)) or m.qualname}",
                  file=sys.stderr)
        return None
    return matches[0]


def _scan_root(root: str | Path):
    """Carve ``root`` into a corpus for a view command, or print an error and return
    None (the shared lint-boundary guard: a missing or source-free root is exit 2).

    View commands answer questions and never judge, so they read only the discovered
    config's scan settings (``exclude``), not its ``[rules]``: a ``.slop.toml`` that names
    a rule slop no longer has (or a bad threshold) is a ``lint`` error, not a reason to
    refuse to print a name's definitions."""
    root = Path(root)
    if not root.exists():
        print(f"slop: error: root path does not exist: {root}", file=sys.stderr)
        return None
    corpus = scan_corpus(root, AnalysisConfig.load(root, RULE_REGISTRY))
    if not _has_source(corpus):
        print(f"slop: error: no source files found under {root}", file=sys.stderr)
        return None
    return corpus


def _view_header(command: str, target: str, summary: str) -> str:
    """One scannable header line shared by the structural views (ast/lexicon/deps):
    ``<command>  <target>  · <summary>``, command left-aligned to a common column."""
    return f"{command:<8} {target}  · {summary}"


def _norm_delta(value: float, norm: float, *, eps: float, qualifier: bool = False) -> str:
    """``(norm 0.49 ↑)`` — how ``value`` sits against a population norm. Within ``eps``
    reads ≈; ``qualifier`` adds steep/flat for the Zipf gradient. The view's whole point
    is making deviation visible without the reader having to know the baseline."""
    d = value - norm
    arrow = "≈" if abs(d) <= eps else ("↑" if d > 0 else "↓")
    if qualifier and arrow != "≈":
        return f"(norm {norm:.2f} {arrow} {'steep' if d > 0 else 'flat'})"
    return f"(norm {norm:.2f} {arrow})"


def _has_source(corpus) -> bool:
    """True if the scanned corpus contains at least one module. A nonexistent or
    source-free root yields an empty corpus; linting it would visit zero components and
    report "clean" — a false pass. The CLI treats that as an error, not a clean run."""
    stack = [corpus]
    while stack:
        component = stack.pop()
        if component.id.kind is ScopeKind.MODULE:
            return True
        stack.extend(component.children())
    return False


def _analyse(root: str | Path, rules=None) -> InferAnalysis | None:
    """Scan ``root`` and run every enabled rule, or only ``rules`` (which then run whether or not
    the config has them enabled). On a missing or source-free root, print the error and return None."""
    root = Path(root)
    if not root.exists():
        print(f"slop: error: root path does not exist: {root}", file=sys.stderr)
        return None
    config = AnalysisConfig.load(root, RULE_REGISTRY)
    if rules is not None:
        config = replace(config, rules={
            **config.rules, **{r.name: replace(config.rules[r.name], enabled=True) for r in rules}})
    corpus = scan_corpus(root, config)
    if not _has_source(corpus):
        print(f"slop: error: no source files found under {root}", file=sys.stderr)
        return None
    report = Dispatcher(RULE_REGISTRY if rules is None else rules, config).run(corpus)
    project_root = config.anchor or (root if root.is_dir() else root.parent)
    return InferAnalysis(root=project_root, report=report, corpus=corpus)


def lint(root: str | Path, output: str = "human", *, rules=None) -> int:
    """Run every enabled rule, or only ``rules``, then apply the project's inference rulings."""
    analysis = _analyse(root, rules)
    if analysis is None:
        return 2
    settlement = settle(analysis, JsonlLedger.at(analysis.root))
    report = settlement.report
    if output == "json":
        print(json.dumps(_with_residue(report.as_dict(), settlement), indent=2))
    else:
        print(_human(report))
    return report.exit_code()


def _with_residue(doc: dict, settlement) -> dict:
    """``doc`` with each finding that can be put to inference carrying its ``residue``."""
    for key in ("violations", "warnings"):
        for entry, finding in zip(doc[key], getattr(settlement.report, key)):
            item = settlement.residue.get(finding.position)
            if item is not None:
                entry["residue"] = dump(item)
    return doc


def check(names: list[str], root: str | Path, output: str = "human") -> int:
    """Run only the named rules, even if the config or the default has them off."""
    by_name = {r.name: r for r in RULE_REGISTRY}
    unknown = [n for n in names if n not in by_name]
    if unknown:
        print(f"slop: unknown rule(s) {unknown}. Try `slop rules`.", file=sys.stderr)
        return 2
    return lint(root, output, rules=[by_name[n] for n in names])


def rules_cmd(output: str = "human") -> int:
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


def doctor() -> int:
    """Report the tools slop relies on."""
    print("slop doctor\n")
    ok = True
    try:
        import tree_sitter  # noqa: F401
        print("  [ok]   tree-sitter (parsing)")
    except Exception as exc:  # noqa: BLE001
        print(f"  [FAIL] tree-sitter not importable: {exc}")
        ok = False
    print("\nready" if ok else "\nmissing required tooling")
    return 0 if ok else 2


def ast_view(path: str | Path, output: str = "human", *,
             raw: bool = False, max_depth: int | None = None) -> int:
    """Print the parse tree of a single source file — the standalone AST inspector.

    Sub-file structure (the scoped items a flat file read discards) made visible before
    acting: read-only seeing, decoupled from doing. Defaults to the named-node skeleton
    (the abstraction); ``raw`` keeps every anonymous token (the full transcript)."""
    from .ast import GRAMMARS_BY_ID
    from .ast.parse import detect_language
    from .ast.tree import AST

    path = Path(path)
    if not path.exists():
        print(f"slop: error: path does not exist: {path}", file=sys.stderr)
        return 2
    if path.is_dir():
        print(f"slop: error: {path} is a directory; ast takes a single file", file=sys.stderr)
        return 2
    lang = detect_language(path)
    if lang is None or lang not in GRAMMARS_BY_ID:
        print(f"slop: error: no grammar for {path} (unrecognised language)", file=sys.stderr)
        return 2
    ast = AST.parse(path, GRAMMARS_BY_ID[lang])
    if ast is None:
        print(f"slop: error: could not parse {path}", file=sys.stderr)
        return 2

    named_only = not raw
    if output == "json":
        print(json.dumps(ast.root.to_dict(named_only=named_only, max_depth=max_depth), indent=2))
    else:
        body = ast.render(named_only=named_only, max_depth=max_depth)
        print(_view_header("ast", str(path), f"{body.count(chr(10)) + 1} nodes"))
        print(body)
    return 0


def lexicon_view(root: str | Path, output: str = "human", *,
                 scope: str | None = None, top: int = 15,
                 scope_kind: str | None = None, ontology: str | Path | None = None) -> int:
    """Print a scope's vocabulary distribution — the lexical skeleton.

    Precise (any scope via ``--scope``, not just the corpus), abstract (the Zipf
    distribution + head, not a token dump), current (regenerated from the fresh carve).
    With ``--ontology``, also compares the observed tokens with a canonical vocabulary
    (see ``slop.lexical``)."""
    corpus = _scan_root(root)
    if corpus is None:
        return 2
    target = corpus
    if scope is not None:
        target = _select_scope(corpus, scope, _parse_kind(scope_kind))
        if target is None:
            return 2
    vocabulary = OntologyIR.load(ontology) if ontology is not None else None
    lexicon = target.lexicon()
    dist = lexicon.distribution(top=top)
    cov = (lexical_coverage(build_declared_lexicon(target), vocabulary)
           if vocabulary is not None else None)
    label = _rel_path(target.id, str(corpus.root)) or target.qualname or corpus.name
    if output == "json":
        payload = {"scope": label, "kind": target.id.kind.value, **dist.as_dict()}
        if cov is not None:
            payload["canonical"] = {"basis": "declared names", **cov.as_dict(top=top)}
        print(json.dumps(payload, indent=2))
    else:
        header = _view_header("lexicon", f"{label} ({target.id.kind.value})",
                              f"{dist.distinct} tokens · {dist.n} occ")
        norms = dist.as_dict()["norms"]
        if dist.distinct >= 15:
            # Enough vocabulary for the Zipf fit / hapax to be meaningful — show deviation.
            stat = (f"  hapax {dist.hapax_ratio:.2f} "
                    f"{_norm_delta(dist.hapax_ratio, norms['hapax_ratio'], eps=0.05)} · "
                    f"Zipf α{dist.zipf_alpha:.2f} "
                    f"{_norm_delta(dist.zipf_alpha, norms['zipf_alpha'], eps=0.15, qualifier=True)} "
                    f"R²{dist.zipf_r2:.2f}")
        else:
            stat = (f"  hapax {dist.hapax_ratio:.2f} · Zipf α{dist.zipf_alpha:.2f} "
                    f"R²{dist.zipf_r2:.2f} · small sample (norms suppressed)")
        top_line = "  top: " + " ".join(f"{t}({c})" for t, c in dist.top) if dist.top else "  top: —"
        lines = [header, stat, top_line]
        if cov is not None:
            pct = 100 * cov.occurrences_covered / cov.occurrences_total
            lines.append(f"  vocabulary {cov.vocabulary}, over declared names: "
                         f"{cov.occurrences_covered}/{cov.occurrences_total} occurrences "
                         f"({pct:.0f}%) · "
                         f"{len(cov.covered)}/{len(cov.covered) + len(cov.undefined)} tokens defined")
            lines.append(f"  undefined (most used first, top {min(top, len(cov.undefined))} of "
                         f"{len(cov.undefined)}): "
                         + (" ".join(f"{o.token}({o.count}×,{o.files}f)" for o in cov.undefined[:top])
                            or "—"))
            lines.append("  unused canonical: " + (" ".join(cov.unused) or "—"))
            if cov.unmeasurable:
                lines.append("  unmeasurable (stripped as noise): " + " ".join(cov.unmeasurable))
        print("\n".join(lines))
    return 0


def deps_view(root: str | Path, output: str = "human", *,
              scope: str | None = None, cycles_only: bool = False) -> int:
    """Print the module dependency graph — the relational skeleton.

    Edges carry the ``resolved`` flag rather than forcing precision: an external or
    bare-specifier import shows as unresolved instead of a false edge. ``--scope``
    restricts to edges touching one module; ``--cycles`` shows only import cycles."""
    corpus = _scan_root(root)
    if corpus is None:
        return 2
    graph = corpus.context.dep_graph if corpus.context else None
    if graph is None:
        print("slop: error: no dependency graph available", file=sys.stderr)
        return 2

    root = str(corpus.root)

    def label(scope_id) -> str:
        # Modules' bare-stem qualnames collide across packages; the relative path is the
        # unambiguous node label.
        return _rel_path(scope_id, root) or scope_id.qualname

    edges = list(graph.edges())
    if scope is not None:
        target = _select_scope(corpus, scope)  # validates: errors on unknown/ambiguous
        if target is None:
            return 2
        keys = {target.qualname, _rel_path(target.id, root)}
        edges = [e for e in edges
                 if {e.from_.qualname, label(e.from_)} & keys
                 or (e.to is not None and {e.to.qualname, label(e.to)} & keys)]
    cycles = graph.cycles()
    modules = [c for c in _walk(corpus) if c.id.kind is ScopeKind.MODULE]
    n_unresolved = sum(1 for e in edges if not e.resolved)

    if output == "json":
        print(json.dumps({
            "modules": len(modules),
            "edges": [{"from": label(e.from_),
                       "to": label(e.to) if e.to is not None else None,
                       "kind": e.kind, "resolved": e.resolved,
                       "raw_specifier": e.raw_specifier} for e in edges],
            "cycles": [list(c.members) for c in cycles],
        }, indent=2))
        return 0

    lines = [_view_header("deps", scope or "corpus",
                          f"{len(modules)} modules · {len(edges)} edges · {len(cycles)} cycle(s)")]
    if not cycles_only:
        by_from: dict = {}
        for e in edges:
            if e.resolved and e.to is not None:
                by_from.setdefault(e.from_, set()).add(label(e.to))
        for node in sorted(by_from, key=label):
            tos = ", ".join(sorted(by_from[node]))
            lines.append(f"  {label(node)}  → {tos}   "
                         f"(Ce {graph.efferent(node)} · Ca {graph.afferent(node)})")
        if n_unresolved:
            lines.append(f"  unresolved: {n_unresolved} edge(s) (external / bare specifiers)")
    for c in cycles:
        lines.append("  cycle: " + " ↔ ".join(c.members))
    print("\n".join(lines))
    return 0


def _parse_kind(kind: str | None) -> ScopeKind | None:
    if kind is None:
        return None
    try:
        return ScopeKind(kind)
    except ValueError:
        raise ValueError(
            f"unknown kind '{kind}' (choose from {', '.join(k.value for k in ScopeKind)})"
        ) from None


def _where(match) -> str:
    return f"{match.path}:{match.line}" if match.path and match.line else (match.path or "-")


def find_view(root: str | Path, name: str | None, output: str = "human", *,
              kind: str | None = None, collisions: bool = False) -> int:
    """Where is a name defined, or (``--collisions``) which names are defined twice.

    A fact lookup: exact local name, optional kind. No match is an answer (exit 0)."""
    corpus = _scan_root(root)
    if corpus is None:
        return 2
    scope_kind = _parse_kind(kind)
    if collisions:
        collision_kind = scope_kind or ScopeKind.CLASS
        groups = discovery.collisions(corpus, kind=collision_kind)
        notes = discovery.caveats(corpus, collision_kind)
        if output == "json":
            print(json.dumps({"kind": collision_kind.value,
                              "collisions": {n: [m.as_dict() for m in ms]
                                             for n, ms in groups.items()},
                              "caveats": notes}, indent=2))
            return 0
        lines = [_view_header("find", "collisions",
                              f"{len(groups)} name(s) defined more than once")]
        for n, ms in groups.items():
            lines.append(f"  {n}  x{len(ms)}")
            lines.extend(f"    {m.qualname}  {_where(m)}" for m in ms)
        lines.extend(f"  note: {n}" for n in notes)
        print("\n".join(lines))
        return 0
    if name is None:
        raise ValueError("find needs a NAME, or --collisions")
    matches = discovery.find(corpus, name, kind=scope_kind)
    notes = discovery.caveats(corpus, scope_kind)
    if output == "json":
        print(json.dumps({"name": name, "matches": [m.as_dict() for m in matches],
                          "caveats": notes}, indent=2))
        return 0
    lines = [_view_header("find", name, f"{len(matches)} match(es)")]
    lines.extend(f"  {m.kind.value:<8} {m.qualname}  {_where(m)}" for m in matches)
    lines.extend(f"  note: {n}" for n in notes)
    print("\n".join(lines))
    return 0


def tree_view(root: str | Path, output: str = "human", *, scope: str | None = None,
              depth: int | None = None, kind: str | None = None,
              scope_kind: str | None = None) -> int:
    """What a scope holds: the ownership tree beneath it, one row per scope."""
    corpus = _scan_root(root)
    if corpus is None:
        return 2
    target = corpus
    if scope is not None:
        target = _select_scope(corpus, scope, _parse_kind(scope_kind))
        if target is None:
            return 2
    shown_kind = _parse_kind(kind)
    rows = discovery.outline(target, corpus.root, depth=depth,
                             kinds=frozenset({shown_kind}) if shown_kind else None)
    notes = discovery.caveats(corpus, shown_kind, under=target)
    label = _rel_path(target.id, str(corpus.root)) or target.qualname or corpus.name
    if output == "json":
        print(json.dumps({"scope": label, "kind": target.id.kind.value,
                          "rows": [{"level": level, **m.as_dict()} for level, m in rows],
                          "caveats": notes}, indent=2))
        return 0
    lines = [_view_header("tree", f"{label} ({target.id.kind.value})", f"{len(rows)} scope(s)")]
    lines.extend(f"{'  ' * level}{m.kind.value} {m.name}  {_where(m)}" for level, m in rows)
    lines.extend(f"  note: {n}" for n in notes)
    print("\n".join(lines))
    return 0


def vocab_view(root: str | Path, ontology: str | Path, output: str = "human", *,
               term: str | None = None) -> int:
    """The canonical vocabulary against the code.

    ``--term NAME`` answers what NAME is canonically (no scan needed). Otherwise the
    classes found under ``--root`` are compared with the ontology's entities: matched,
    unknown to the ontology, and declared but unused. Exit 0 whenever the comparison ran;
    gating on mismatches belongs to the lint layer."""
    vocabulary = OntologyIR.load(ontology)
    if term is not None:
        found = vocabulary.term(term)
        if output == "json":
            print(json.dumps({"vocabulary": vocabulary.name, "query": term,
                              "canonical": found.as_dict() if found else None}, indent=2))
        elif found is None:
            print(_view_header("vocab", term, f"not canonical in {vocabulary.name}"))
        else:
            lines = [_view_header("vocab", term, f"{found.kind.value} {found.name} in {vocabulary.name}")]
            if found.description:
                lines.append(f"  {found.description}")
            if found.fields:
                lines.append("  fields: " + ", ".join(found.fields))
            print("\n".join(lines))
        return 0
    corpus = _scan_root(root)
    if corpus is None:
        return 2
    result = compare(discovery.find(corpus, kind=ScopeKind.CLASS), vocabulary)
    notes = discovery.caveats(corpus, ScopeKind.CLASS)
    if output == "json":
        print(json.dumps({"vocabulary": vocabulary.name, **result.as_dict(),
                          "caveats": notes}, indent=2))
        return 0
    lines = [_view_header("vocab", vocabulary.name,
                          f"{len(result.matched)} matched · {len(result.unknown)} unknown · "
                          f"{len(result.unused)} unused")]
    for t, ms in result.matched:
        lines.append(f"  matched  {t.name}  <- " + ", ".join(m.qualname for m in ms))
    for m in result.unknown:
        lines.append(f"  unknown  {m.name}  {_where(m)}")
    for t in result.unused:
        lines.append(f"  unused   {t.name}")
    lines.extend(f"  note: {n}" for n in notes)
    print("\n".join(lines))
    return 0


def shape_view(root: str | Path, output: str = "human", *, scope: str | None = None,
               scope_kind: str | None = None) -> int:
    """The shape of every class beneath a scope: its Chidamber-Kemerer profile and its
    method groups (LCOM4), unfiltered: no limits are applied, so it answers for any class
    (the ``class-*`` rules apply limits to the same numbers). ``lcom4`` is ``null`` where
    the language's instance member access cannot be read from syntax."""
    corpus = _scan_root(root)
    if corpus is None:
        return 2
    target = corpus
    if scope is not None:
        target = _select_scope(corpus, scope, _parse_kind(scope_kind))
        if target is None:
            return 2
    located = discovery.locate(
        (s for s in _walk(target) if s.id.kind is ScopeKind.CLASS), corpus.root)
    rows = [{**match.as_dict(), **Structure.over(cls).ck().as_dict()} for cls, match in located]
    notes = discovery.caveats(corpus, ScopeKind.CLASS, under=target)
    label = _rel_path(target.id, str(corpus.root)) or target.qualname or corpus.name
    if output == "json":
        print(json.dumps({"scope": label, "kind": target.id.kind.value, "classes": rows,
                          "caveats": notes}, indent=2))
        return 0
    lines = [_view_header("shape", f"{label} ({target.id.kind.value})", f"{len(rows)} class(es)")]
    for row in rows:
        lcom4 = "n/a" if row["lcom4"] is None else row["lcom4"]
        where = f"{row['path']}:{row['line']}" if row["path"] and row["line"] else (row["path"] or "-")
        lines.append(f"  {row['name']}  {where}  nom {row['nom']} dit {row['dit']} "
                     f"noc {row['noc']} cbo {row['cbo']} lcom4 {lcom4}")
        if row["method_groups"]:
            lines.append("    groups: " + " ".join("{" + ", ".join(g) + "}" for g in row["method_groups"]))
        if row["detached"]:
            lines.append("    detached: " + ", ".join(row["detached"]))
        lines.extend(f"    note: {c}" for c in row["caveats"])
    lines.extend(f"  note: {n}" for n in notes)
    print("\n".join(lines))
    return 0


def hotspots_view(root: str | Path, output: str = "human", *, since: str | None = None,
                  last: int | None = None) -> int:
    """Files changed in a revision window, ranked by churn x complexity (Tornhill 2015).

    The window is revisions, not time: ``--since REV`` or ``--last N`` commits, plus every
    uncommitted change. No limit is applied; the list is the answer."""
    corpus = _scan_root(root)
    if corpus is None:
        return 2
    if last is None:
        last = DEFAULT_LAST
    rows = Structure.over(corpus).hotspots(since=since, last=last)
    window = f"{since}..HEAD + uncommitted" if since is not None else f"last {last} commits + uncommitted"
    if output == "json":
        print(json.dumps({"window": window, "files": [
            {"path": h.path, "churn": h.churn, "complexity": h.complexity,
             "product": h.churn * h.complexity} for h in rows]}, indent=2))
        return 0
    lines = [_view_header("hotspots", window, f"{len(rows)} file(s) changed")]
    lines.extend(f"  {h.path}  churn {h.churn} x complexity {h.complexity} = {h.churn * h.complexity}"
                 for h in rows)
    print("\n".join(lines))
    return 0


def infer_instructions() -> int:
    """Print the agent's instructions for the inference workflow."""
    print(prose.instructions(), end="")
    return 0


def infer_references(name: str | None) -> int:
    """List the bundled references, or print the one called ``name``."""
    if name is None:
        print("\n".join(prose.references()))
        return 0
    try:
        print(prose.reference(name), end="")
    except KeyError:
        print(f"slop: error: no reference '{name}'. Try `slop infer references`.", file=sys.stderr)
        return 2
    return 0


def infer_schema(name: str | None) -> int:
    """Print the JSON Schema of every document an agent and slop exchange, or of one."""
    schemas = infer_schemas()
    print(json.dumps(schemas if name is None else schemas[name], indent=2))
    return 0


def infer_apply(file: str, root: str | Path) -> int:
    """Read a verdicts document (a file, or ``-`` for stdin), store what is acceptable, and print
    the receipt. Exit 1 if any verdict was rejected, 2 if the document is not valid."""
    text = sys.stdin.read() if file == "-" else Path(file).read_text(encoding="utf-8")
    try:
        verdicts = parse(Verdicts, json.loads(text))
    except (json.JSONDecodeError, ContractError) as exc:
        print(f"slop: error: {exc}", file=sys.stderr)
        return 2
    analysis = _analyse(root)
    if analysis is None:
        return 2
    inferable = {item.id: item for item in FindingSource().residue(analysis)}
    receipt = route(verdicts, inferable, JsonlLedger.at(analysis.root),
                    at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    print(json.dumps(dump(receipt), indent=2))
    return 1 if receipt.rejected else 0


def skill_list() -> int:
    """List the skills slop ships."""
    for name, skill in sorted(SKILLS.items()):
        print(f"{name}  {skill.description}")
    return 0


def skill_show(name: str, file: str | None) -> int:
    """Print a skill's SKILL.md, or the file at ``file`` inside it."""
    skill = _skill(name)
    if skill is None:
        return 2
    tree = skill.tree()
    shown = "SKILL.md" if file is None else file
    if shown not in tree:
        print(f"slop: error: skill '{name}' has no file '{shown}'. Its files: {', '.join(tree)}", file=sys.stderr)
        return 2
    print(tree[shown], end="")
    return 0


def skill_install(name: str, dest: str, force: bool) -> int:
    """Write a skill's directory under ``dest`` and print where."""
    skill = _skill(name)
    if skill is None:
        return 2
    try:
        print(install_skill(skill, Path(dest), replace=force))
    except InstallError as exc:
        print(f"slop: error: {exc}", file=sys.stderr)
        return 2
    return 0


def _skill(name: str):
    """The skill called ``name``, or None after printing why there is none."""
    if name not in SKILLS:
        print(f"slop: error: no skill '{name}'. Try `slop skill list`.", file=sys.stderr)
        return None
    return SKILLS[name]


def init(root: str | Path) -> int:
    """Emit a ``.slop.toml`` template from each rule's default config."""
    path = Path(root) / CONFIG_FILENAME
    if path.exists():
        print(f"slop: {path} already exists; not overwriting", file=sys.stderr)
        return 2
    path.write_text(_template())
    print(f"wrote {path}")
    return 0


def _template() -> str:
    lines = ["# slop configuration, generated by `slop init`.",
             "# Uncomment and edit to change a rule's defaults.\n",
             '# exclude = ["tests/**"]       # files slop never reads\n']
    for r in sorted(RULE_REGISTRY, key=lambda x: x.name):
        rc = r.default_config()
        lines.append(f"# [rules.{r.name}]")
        lines.append(f"# enabled = {str(rc.enabled).lower()}")
        for key, value in rc.options.items():
            lines.append(f"# {key} = {json.dumps(value)}")
        lines.append("")
    return "\n".join(lines)


def _human(report: Report) -> str:
    """One ``path:line:column: rule message`` line per violation, the shape editors and
    other tools already parse; then one ``WARN`` line per subjective finding; then a summary."""
    def where(v) -> str:
        return f"{report.relative_path(v) or '<corpus>'}:{v.line}:{v.column}"

    lines = [f"{where(v)}: {v.rule} {v.message}" for v in report.violations]
    lines += [f"{where(v)}: WARN {v.rule} {v.message}" for v in report.warnings]
    errors, warnings = len(report.violations), len(report.warnings)
    head = f"Found {errors} violation{'s' if errors != 1 else ''}" if errors else "No violations"
    tail = f" and {warnings} warning{'s' if warnings != 1 else ''}" if warnings else ""
    lines.append(f"{head}{tail}.")
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    """Every command, each with the function it runs as ``run``."""
    parser = argparse.ArgumentParser(prog="slop", description="a linter and code-structure query tool")
    parser.add_argument("--version", action="version", version=f"slop {_version()}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_lint = sub.add_parser("lint", help="lint a source root")
    p_lint.add_argument("--root", default=".", help="source root to scan (default: cwd)")
    p_lint.add_argument("--output", choices=["human", "json"], default="human")
    p_lint.set_defaults(run=lambda a: lint(a.root, a.output))

    p_check = sub.add_parser("check", help="run only the named rules")
    p_check.add_argument("rules", nargs="+", help="rule name(s) to run (see `slop rules`)")
    p_check.add_argument("--root", default=".")
    p_check.add_argument("--output", choices=["human", "json"], default="human")
    p_check.set_defaults(run=lambda a: check(a.rules, a.root, a.output))

    p_rules = sub.add_parser("rules", help="list the rule registry")
    p_rules.add_argument("--output", choices=["human", "json"], default="human")
    p_rules.set_defaults(run=lambda a: rules_cmd(a.output))

    sub.add_parser("doctor", help="check slop's tooling dependencies").set_defaults(run=lambda a: doctor())

    p_init = sub.add_parser("init", help="write a .slop.toml config template")
    p_init.add_argument("--root", default=".")
    p_init.set_defaults(run=lambda a: init(a.root))

    p_ast = sub.add_parser("ast", help="print the parse tree of a single source file")
    p_ast.add_argument("path", help="source file to inspect")
    p_ast.add_argument("--output", choices=["human", "json"], default="human")
    p_ast.add_argument("--raw", action="store_true",
                       help="keep anonymous tokens (full transcript); default is the named skeleton")
    p_ast.add_argument("--max-depth", type=int, default=None,
                       help="truncate the tree below this depth")
    p_ast.set_defaults(run=lambda a: ast_view(a.path, a.output, raw=a.raw, max_depth=a.max_depth))

    p_lex = sub.add_parser("lexicon", help="print a scope's vocabulary distribution")
    p_lex.add_argument("--root", default=".")
    p_lex.add_argument("--scope", default=None, help="qualname of a sub-scope (default: whole corpus)")
    p_lex.add_argument("--scope-kind", default=None,
                       help="pick one kind when --scope names several (a package and its __init__ module)")
    p_lex.add_argument("--top", type=int, default=15, help="number of top tokens to show")
    p_lex.add_argument("--ontology", default=None,
                       help="Open Ontology IR JSON: also report coverage of the observed tokens")
    p_lex.add_argument("--output", choices=["human", "json"], default="human")
    p_lex.set_defaults(run=lambda a: lexicon_view(a.root, a.output, scope=a.scope, top=a.top,
                                                  scope_kind=a.scope_kind, ontology=a.ontology))

    p_deps = sub.add_parser("deps", help="print the module dependency graph")
    p_deps.add_argument("--root", default=".")
    p_deps.add_argument("--scope", default=None, help="restrict to edges touching this module qualname")
    p_deps.add_argument("--cycles", action="store_true", help="show only import cycles")
    p_deps.add_argument("--output", choices=["human", "json"], default="human")
    p_deps.set_defaults(run=lambda a: deps_view(a.root, a.output, scope=a.scope, cycles_only=a.cycles))

    p_find = sub.add_parser("find", help="where a name is defined (or which names collide)")
    p_find.add_argument("name", nargs="?", default=None, help="exact local name to look up")
    p_find.add_argument("--root", default=".")
    p_find.add_argument("--kind", default=None, help="restrict to one scope kind (class, callable, ...)")
    p_find.add_argument("--collisions", action="store_true",
                        help="list names defined by more than one scope of --kind (default class)")
    p_find.add_argument("--output", choices=["human", "json"], default="human")
    p_find.set_defaults(run=lambda a: find_view(a.root, a.name, a.output, kind=a.kind, collisions=a.collisions))

    p_tree = sub.add_parser("tree", help="print the ownership tree beneath a scope")
    p_tree.add_argument("--root", default=".")
    p_tree.add_argument("--scope", default=None, help="qualname or path of a sub-scope (default: whole corpus)")
    p_tree.add_argument("--depth", type=int, default=None, help="levels below the scope to show")
    p_tree.add_argument("--kind", default=None, help="show only scopes of this kind")
    p_tree.add_argument("--scope-kind", default=None,
                        help="pick one kind when --scope names several (a package and its __init__ module)")
    p_tree.add_argument("--output", choices=["human", "json"], default="human")
    p_tree.set_defaults(run=lambda a: tree_view(a.root, a.output, scope=a.scope, depth=a.depth,
                                                kind=a.kind, scope_kind=a.scope_kind))

    p_vocab = sub.add_parser("vocab", help="compare code names with a canonical ontology (JSON IR)")
    p_vocab.add_argument("--ontology", required=True, help="Open Ontology IR JSON file")
    p_vocab.add_argument("--root", default=".")
    p_vocab.add_argument("--term", default=None, help="print this term's canonical entry instead of comparing")
    p_vocab.add_argument("--output", choices=["human", "json"], default="human")
    p_vocab.set_defaults(run=lambda a: vocab_view(a.root, a.ontology, a.output, term=a.term))

    p_shape = sub.add_parser("shape", help="print each class's CK profile and cohesion groups")
    p_shape.add_argument("--root", default=".")
    p_shape.add_argument("--scope", default=None, help="qualname or path of the scope to report beneath")
    p_shape.add_argument("--scope-kind", default=None,
                         help="pick one kind when --scope names several (a package and its __init__ module)")
    p_shape.add_argument("--output", choices=["human", "json"], default="human")
    p_shape.set_defaults(run=lambda a: shape_view(a.root, a.output, scope=a.scope, scope_kind=a.scope_kind))

    p_hot = sub.add_parser("hotspots", help="files ranked by recent churn x complexity")
    p_hot.add_argument("--root", default=".")
    window = p_hot.add_mutually_exclusive_group()
    window.add_argument("--since", default=None, metavar="REV",
                        help="commits in REV..HEAD plus uncommitted changes (HEAD = uncommitted only)")
    window.add_argument("--last", type=int, default=None, metavar="N",
                        help=f"the last N commits plus uncommitted changes (default {DEFAULT_LAST})")
    p_hot.add_argument("--output", choices=["human", "json"], default="human")
    p_hot.set_defaults(run=lambda a: hotspots_view(a.root, a.output, since=a.since, last=a.last))

    p_infer = sub.add_parser("infer", help="inference over the linter's subjective findings: verdicts, rubrics, schemas")
    infer_sub = p_infer.add_subparsers(dest="infer_command", required=True)
    infer_sub.add_parser("instructions", help="print the agent's instructions for the inference workflow").set_defaults(
        run=lambda a: infer_instructions())
    p_refs = infer_sub.add_parser("references", help="list the bundled references, or print one")
    p_refs.add_argument("name", nargs="?", default=None, help="a name from the list (for example rubrics/class-cohesion)")
    p_refs.set_defaults(run=lambda a: infer_references(a.name))
    p_schema = infer_sub.add_parser("schema", help="print the JSON Schema of the documents the exchange uses")
    p_schema.add_argument("name", nargs="?", default=None, choices=sorted(infer_schemas()),
                          help="one document (default: all)")
    p_schema.set_defaults(run=lambda a: infer_schema(a.name))
    p_apply = infer_sub.add_parser("apply", help="store verdicts from a file or stdin and print a receipt")
    p_apply.add_argument("file", nargs="?", default="-", help="verdicts JSON (default: stdin)")
    p_apply.add_argument("--root", default=".")
    p_apply.set_defaults(run=lambda a: infer_apply(a.file, a.root))

    p_skill = sub.add_parser("skill", help="Agent Skills that teach an agent to use slop")
    skill_sub = p_skill.add_subparsers(dest="skill_command", required=True)
    skill_sub.add_parser("list", help="list the skills slop ships").set_defaults(run=lambda a: skill_list())
    p_show = skill_sub.add_parser("show", help="print a skill's SKILL.md, or one of its files")
    p_show.add_argument("name")
    p_show.add_argument("file", nargs="?", default=None, help="a path inside the skill (default: SKILL.md)")
    p_show.set_defaults(run=lambda a: skill_show(a.name, a.file))
    p_install = skill_sub.add_parser("install", help="write a skill's directory under DEST")
    p_install.add_argument("name")
    p_install.add_argument("--dest", required=True, help="the skills directory, e.g. .claude/skills")
    p_install.add_argument("--force", action="store_true", help="replace an existing install of this skill")
    p_install.set_defaults(run=lambda a: skill_install(a.name, a.dest, a.force))

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.run(args)
    except Exception as exc:  # noqa: BLE001 — top-level boundary: any failure is exit 2
        print(f"slop: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
