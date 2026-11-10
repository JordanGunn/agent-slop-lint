"""slop CLI.

Primitives (read-only views over the layers): ``ast`` / ``tree`` / ``find`` / ``lexicon`` /
``deps`` / ``vocab``. Lint layer: ``lint`` / ``check`` / ``rules``. Housekeeping:
``doctor`` / ``init`` / ``schema``.

The primitives answer questions and exit 0 whenever they answered (an empty result is an
answer); 2 means the question could not be answered. The lint layer exits 0 clean /
1 on any ERROR finding / 2 on error.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from importlib.metadata import PackageNotFoundError, version as _pkg_version
from pathlib import Path

from .config import AnalysisConfig
from .dispatch import Dispatcher, Report
from .finding import Severity
from .scope import scan_corpus
from .scope.identity import ScopeKind
from .rules import RULE_REGISTRY
from .ontology import OntologyIR, compare
from .scope import find as discovery
from .scope.find import relative_path as _rel_path, walk as _walk


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
    None (the shared lint-boundary guard: a missing or source-free root is exit 2)."""
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


def lint(root: str | Path, output: str = "human", *, rules=RULE_REGISTRY) -> int:
    root = Path(root)
    if not root.exists():
        print(f"slop: error: root path does not exist: {root}", file=sys.stderr)
        return 2
    # Config is always validated against the FULL registry (a configured rule outside
    # the dispatched subset is still a known rule); only `rules` are dispatched. This
    # is what lets `check <family>` run with an ancestor config that configures other
    # rules without raising "configures unknown rule".
    config = AnalysisConfig.load(root, RULE_REGISTRY)
    corpus = scan_corpus(root, config)
    if not _has_source(corpus):
        print(f"slop: error: no source files found under {root}", file=sys.stderr)
        return 2
    report = Dispatcher(rules, config).run(corpus)
    if output == "json":
        print(json.dumps(report.as_dict(), indent=2))
    else:
        print(_human(report))
    return report.exit_code()


def check(target: str, root: str | Path, output: str = "human") -> int:
    """Lint with only the rules matching ``target`` — an exact rule name
    (``complexity.cyclomatic``) or a namespace family (``complexity``)."""
    selected = [r for r in RULE_REGISTRY
                if r.name == target or r.name.startswith(target + ".")]
    if not selected:
        print(f"slop: no rule or family matches '{target}'. Try `slop rules`.", file=sys.stderr)
        return 2
    return lint(root, output, rules=selected)


def rules_cmd(output: str = "human") -> int:
    """List the rule registry: name, altitudes, disposition."""
    rows = []
    for r in sorted(RULE_REGISTRY, key=lambda x: x.name):
        rc = r.default_config()
        alts = ",".join(sorted(k.value for k in r.altitudes))
        # A rule whose default severity is INFO emits observations; otherwise verdicts.
        dispo = "observation" if rc.severity is Severity.INFO else f"verdict/{rc.severity.label()}"
        rows.append((r.name, alts, dispo))
    if output == "json":
        print(json.dumps([{"name": n, "altitudes": a, "disposition": d} for n, a, d in rows], indent=2))
        return 0
    width = max((len(n) for n, _, _ in rows), default=4)
    print(f"{len(rows)} rules\n")
    for n, a, d in rows:
        print(f"  {n:<{width}}  {d:<18}  [{a}]")
    return 0


def schema_cmd(output: str = "json") -> int:
    """Emit the config shape, generated from the registry (so it cannot drift from
    the rules it describes — unlike a hand-maintained asset)."""
    rules_schema = []
    for r in sorted(RULE_REGISTRY, key=lambda x: x.name):
        rc = r.default_config()
        rules_schema.append({
            "name": r.name,
            "altitudes": sorted(k.value for k in r.altitudes),
            "enabled": rc.enabled,
            "severity": rc.severity.label(),
            "thresholds": dict(rc.thresholds),
            "params": dict(rc.params),
        })
    schema = {
        "version": "v1",
        "ignore": {"functions": [], "classes": [], "modules": [], "packages": []},
        "rules": rules_schema,
    }
    if output == "json":
        print(json.dumps(schema, indent=2))
    else:
        print(f"slop config schema v1 — {len(rules_schema)} rules")
        print("  [ignore] scopes: functions, classes, modules, packages")
        for r in rules_schema:
            keys = sorted({*r["thresholds"], *r["params"]})
            print(f"  {r['name']}: severity={r['severity']} keys={keys}")
    return 0


def doctor() -> int:
    """Report the tools slop relies on. Missing optional tools degrade gracefully."""
    print("slop doctor\n")
    ok = True
    try:
        import tree_sitter  # noqa: F401
        print("  [ok]   tree-sitter (parsing)")
    except Exception as exc:  # noqa: BLE001
        print(f"  [FAIL] tree-sitter not importable: {exc}")
        ok = False
    if shutil.which("git"):
        print("  [ok]   git (hotspots churn signal)")
    else:
        print("  [warn] git not found — the hotspots rule will be silent")
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
                 scope_kind: str | None = None) -> int:
    """Print a scope's vocabulary distribution — the lexical skeleton.

    Precise (any scope via ``--scope``, not just the corpus), abstract (the Zipf
    distribution + head, not a token dump), current (regenerated from the fresh carve).
    The same measured object the ``vocabulary`` observation surfaces."""
    corpus = _scan_root(root)
    if corpus is None:
        return 2
    target = corpus
    if scope is not None:
        target = _select_scope(corpus, scope, _parse_kind(scope_kind))
        if target is None:
            return 2
    dist = target.lexicon().distribution(top=top)
    label = _rel_path(target.id, str(corpus.root)) or target.qualname or corpus.name
    if output == "json":
        print(json.dumps({"scope": label, "kind": target.id.kind.value,
                          **dist.as_dict()}, indent=2))
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
        print("\n".join([header, stat, top_line]))
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
    notes = discovery.caveats(corpus, shown_kind)
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


def init(root: str | Path) -> int:
    """Emit a ``.slop.toml`` template from each rule's default config."""
    path = Path(root) / ".slop.toml"
    if path.exists():
        print(f"slop: {path} already exists; not overwriting", file=sys.stderr)
        return 2
    path.write_text(_template())
    print(f"wrote {path}")
    return 0


def _template() -> str:
    lines = ["# slop configuration — generated by `slop init`.",
             "# Uncomment and edit to override a rule's defaults.\n"]
    for r in sorted(RULE_REGISTRY, key=lambda x: x.name):
        rc = r.default_config()
        lines.append(f'# [rules."{r.name}"]')
        lines.append(f"# enabled = {str(rc.enabled).lower()}")
        if rc.severity is not Severity.INFO:
            lines.append(f'# severity = "{rc.severity.label()}"')
        for k, v in rc.thresholds.items():
            lines.append(f"# thresholds.{k} = {json.dumps(v)}")
        for k, v in rc.params.items():
            lines.append(f"# params.{k} = {json.dumps(v)}")
        lines.append("")
    return "\n".join(lines)


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
    parser.add_argument("--version", action="version", version=f"slop {_version()}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_lint = sub.add_parser("lint", help="lint a source root")
    p_lint.add_argument("--root", default=".", help="source root to scan (default: cwd)")
    p_lint.add_argument("--output", choices=["human", "json"], default="human")

    p_check = sub.add_parser("check", help="lint with only one rule or namespace family")
    p_check.add_argument("target", help="a rule name (complexity.cyclomatic) or family (complexity)")
    p_check.add_argument("--root", default=".")
    p_check.add_argument("--output", choices=["human", "json"], default="human")

    p_rules = sub.add_parser("rules", help="list the rule registry")
    p_rules.add_argument("--output", choices=["human", "json"], default="human")

    sub.add_parser("doctor", help="check slop's tooling dependencies")

    p_init = sub.add_parser("init", help="write a .slop.toml config template")
    p_init.add_argument("--root", default=".")

    p_schema = sub.add_parser("schema", help="print the config schema (generated from the registry)")
    p_schema.add_argument("--output", choices=["human", "json"], default="json")

    p_ast = sub.add_parser("ast", help="print the parse tree of a single source file")
    p_ast.add_argument("path", help="source file to inspect")
    p_ast.add_argument("--output", choices=["human", "json"], default="human")
    p_ast.add_argument("--raw", action="store_true",
                       help="keep anonymous tokens (full transcript); default is the named skeleton")
    p_ast.add_argument("--max-depth", type=int, default=None,
                       help="truncate the tree below this depth")

    p_lex = sub.add_parser("lexicon", help="print a scope's vocabulary distribution")
    p_lex.add_argument("--root", default=".")
    p_lex.add_argument("--scope", default=None, help="qualname of a sub-scope (default: whole corpus)")
    p_lex.add_argument("--scope-kind", default=None,
                       help="pick one kind when --scope names several (a package and its __init__ module)")
    p_lex.add_argument("--top", type=int, default=15, help="number of top tokens to show")
    p_lex.add_argument("--output", choices=["human", "json"], default="human")

    p_deps = sub.add_parser("deps", help="print the module dependency graph")
    p_deps.add_argument("--root", default=".")
    p_deps.add_argument("--scope", default=None, help="restrict to edges touching this module qualname")
    p_deps.add_argument("--cycles", action="store_true", help="show only import cycles")
    p_deps.add_argument("--output", choices=["human", "json"], default="human")

    p_find = sub.add_parser("find", help="where a name is defined (or which names collide)")
    p_find.add_argument("name", nargs="?", default=None, help="exact local name to look up")
    p_find.add_argument("--root", default=".")
    p_find.add_argument("--kind", default=None, help="restrict to one scope kind (class, callable, ...)")
    p_find.add_argument("--collisions", action="store_true",
                        help="list names defined by more than one scope of --kind (default class)")
    p_find.add_argument("--output", choices=["human", "json"], default="human")

    p_tree = sub.add_parser("tree", help="print the ownership tree beneath a scope")
    p_tree.add_argument("--root", default=".")
    p_tree.add_argument("--scope", default=None, help="qualname or path of a sub-scope (default: whole corpus)")
    p_tree.add_argument("--depth", type=int, default=None, help="levels below the scope to show")
    p_tree.add_argument("--kind", default=None, help="show only scopes of this kind")
    p_tree.add_argument("--scope-kind", default=None,
                        help="pick one kind when --scope names several (a package and its __init__ module)")
    p_tree.add_argument("--output", choices=["human", "json"], default="human")

    p_vocab = sub.add_parser("vocab", help="compare code names with a canonical ontology (JSON IR)")
    p_vocab.add_argument("--ontology", required=True, help="Open Ontology IR JSON file")
    p_vocab.add_argument("--root", default=".")
    p_vocab.add_argument("--term", default=None, help="print this term's canonical entry instead of comparing")
    p_vocab.add_argument("--output", choices=["human", "json"], default="human")

    args = parser.parse_args(argv)
    try:
        if args.command == "lint":
            return lint(args.root, args.output)
        if args.command == "check":
            return check(args.target, args.root, args.output)
        if args.command == "rules":
            return rules_cmd(args.output)
        if args.command == "doctor":
            return doctor()
        if args.command == "init":
            return init(args.root)
        if args.command == "schema":
            return schema_cmd(args.output)
        if args.command == "ast":
            return ast_view(args.path, args.output, raw=args.raw, max_depth=args.max_depth)
        if args.command == "lexicon":
            return lexicon_view(args.root, args.output, scope=args.scope, top=args.top,
                                scope_kind=args.scope_kind)
        if args.command == "deps":
            return deps_view(args.root, args.output, scope=args.scope, cycles_only=args.cycles)
        if args.command == "find":
            return find_view(args.root, args.name, args.output,
                             kind=args.kind, collisions=args.collisions)
        if args.command == "tree":
            return tree_view(args.root, args.output, scope=args.scope,
                             depth=args.depth, kind=args.kind, scope_kind=args.scope_kind)
        if args.command == "vocab":
            return vocab_view(args.root, args.ontology, args.output, term=args.term)
    except Exception as exc:  # noqa: BLE001 — top-level boundary: any failure is exit 2
        print(f"slop: error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
