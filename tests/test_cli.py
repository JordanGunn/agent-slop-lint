"""CLI subcommands — rules / check / doctor / init (plus the existing lint)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from slop import cli


def test_version_flag_prints_and_exits_zero(capsys):
    # `--version` is a top-level flag: argparse prints and exits(0) before the
    # required-subcommand check, so `slop --version` works without a subcommand.
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert out.startswith("slop ")
    assert cli.version() in out


def test_version_helper_resolves_installed_distribution():
    # The package is installed (editable) in the dev env, so metadata resolves to a
    # real version rather than the source-tree "unknown" fallback.
    assert cli.version() != "unknown"


def test_rules_lists_registry(capsys):
    rc = cli.lint.rules("human")
    out = capsys.readouterr().out
    assert rc == 0
    assert "cyclomatic-complexity" in out
    assert "rules" in out


def test_rules_json(capsys):
    rc = cli.lint.rules("json")
    data = json.loads(capsys.readouterr().out)
    assert rc == 0
    by_name = {r["name"]: r for r in data}
    assert "cyclomatic-complexity" in by_name and "class-coupling" in by_name
    assert len(by_name) == 15
    subjective = {n for n, r in by_name.items() if r["subjective"]}
    assert subjective == {"class-cohesion", "rigid-package", "useless-package"}
    assert all(r["enabled"] for r in by_name.values())
    assert by_name["cyclomatic-complexity"]["altitudes"] == ["callable"]


def test_rules_human_marks_subjective_rules(capsys):
    cli.lint.rules("human")
    lines = capsys.readouterr().out.splitlines()
    [cohesion] = [ln for ln in lines if "class-cohesion" in ln]
    [cyclomatic] = [ln for ln in lines if "cyclomatic-complexity" in ln]
    assert " subjective " in cohesion and " objective " in cyclomatic


def test_check_unknown_target_errors(capsys):
    assert cli.lint.check(["nonsense-rule"], ".", "human") == 2


def test_a_family_or_prefix_is_not_a_rule(capsys):
    assert cli.lint.check(["complexity"], ".", "human") == 2
    assert cli.lint.check(["cyclomatic"], ".", "human") == 2


def test_nonexistent_root_errors(tmp_path: Path, capsys):
    # A missing root must error (exit 2), not report "clean": the CLI-boundary form
    # of "not-flagged != clean".
    missing = tmp_path / "does-not-exist"
    assert cli.lint.lint(missing, "human") == 2
    assert "does not exist" in capsys.readouterr().err


def test_empty_root_errors(tmp_path: Path, capsys):
    # An existing root with no source files would visit zero components and read as
    # clean; that is a false pass, so it errors.
    (tmp_path / "notes.txt").write_text("not source\n")
    assert cli.lint.lint(tmp_path, "human") == 2
    assert "no source files" in capsys.readouterr().err


_TANGLED = "def f(a, b):\n" + "".join(f"    if a == {i}: b += {i}\n" for i in range(15)) + "    return b\n"


def test_lint_human_output_is_one_located_line_per_violation(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(_TANGLED)
    assert cli.lint.lint(tmp_path, "human") == 1
    lines = capsys.readouterr().out.splitlines()
    cyclomatic = [ln for ln in lines if " cyclomatic-complexity " in ln]
    assert len(cyclomatic) == 1
    assert cyclomatic[0].startswith("m.py:1:1: cyclomatic-complexity ")
    assert "16" in cyclomatic[0] and "limit 10" in cyclomatic[0]
    assert lines[-1] == f"Found {len(lines) - 1} violations."


def test_lint_human_output_uses_the_singular_for_one_violation(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(_BRANCHY)
    (tmp_path / ".slop.toml").write_text(_LOW)
    assert cli.lint.lint(tmp_path, "human") == 1
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 2 and lines[0].startswith("m.py:1:1: cyclomatic-complexity ")
    assert lines[1] == "Found 1 violation."


def test_lint_clean_source_exits_zero_with_no_violations(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text("def f(x):\n    return x\n")
    assert cli.lint.lint(tmp_path, "human") == 0
    assert capsys.readouterr().out.strip() == "No violations."


def test_lint_json_shape(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(_TANGLED)
    code, doc = _lint_json(tmp_path, capsys)
    assert code == 1 and set(doc) == {"root", "project_root", "summary", "violations", "warnings", "zero_visited",
                                      "agglomerations"}
    assert doc["summary"] == {"violations": len(doc["violations"]), "warnings": 0, "exit_code": 1}
    assert "findings" not in doc
    v = next(v for v in doc["violations"] if v["rule"] == "cyclomatic-complexity")
    assert v == {"rule": "cyclomatic-complexity", "path": "m.py", "line": 1, "column": 1,
                 "message": v["message"], "value": 16, "threshold": 10, "subject": "m.f",
                 "scope": {"kind": "callable", "qualname": "m.f", "path": "m.py"}, "related": [],
                 "id": v["id"]}
    assert len({f["id"] for f in doc["violations"]}) == len(doc["violations"])


def test_lint_json_of_clean_source(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text("def f(x):\n    return x\n")
    code, doc = _lint_json(tmp_path, capsys)
    assert code == 0 and doc["violations"] == [] and doc["summary"] == {"violations": 0, "warnings": 0, "exit_code": 0}


def test_check_runs_only_the_named_rules(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(_TANGLED)
    code, doc = _lint_json(tmp_path, capsys, check=["cyclomatic-complexity"])
    assert code == 1 and {v["rule"] for v in doc["violations"]} == {"cyclomatic-complexity"}
    _, several = _lint_json(tmp_path, capsys, check=["cyclomatic-complexity", "npath-complexity"])
    assert {v["rule"] for v in several["violations"]} == {"cyclomatic-complexity", "npath-complexity"}


def test_check_exits_zero_when_its_rules_are_clean_though_others_are_not(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(_TANGLED)
    code, doc = _lint_json(tmp_path, capsys, check=["god-module"])
    assert code == 0 and doc["violations"] == []


def test_check_with_a_config_for_another_rule(tmp_path: Path, capsys):
    (tmp_path / ".slop.toml").write_text("[rules.god-module]\nenabled = false\n")
    (tmp_path / "m.py").write_text("def f(x): return x\n")
    assert cli.lint.check(["cyclomatic-complexity"], tmp_path, "json") == 0


def test_an_invalid_config_is_exit_two_not_a_clean_run(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(_TANGLED)
    (tmp_path / ".slop.toml").write_text('[rules.cyclomatic-complexity]\nseverity = "warning"\n')
    assert cli.main(["lint", "--root", str(tmp_path)]) == 2
    assert "severity" in capsys.readouterr().err


def test_a_disabled_rule_reports_nothing_but_check_still_runs_it(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(_TANGLED)
    (tmp_path / ".slop.toml").write_text("[rules.cyclomatic-complexity]\nenabled = false\n")
    _, doc = _lint_json(tmp_path, capsys)
    assert "cyclomatic-complexity" not in {v["rule"] for v in doc["violations"]}
    code, named = _lint_json(tmp_path, capsys, check=["cyclomatic-complexity"])
    assert code == 1 and {v["rule"] for v in named["violations"]} == {"cyclomatic-complexity"}


def test_a_subjective_rule_warns_and_never_fails_the_run(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(
        "class A:\n    def f(self): return self.a\n    def g(self): return self.b\n")
    code, doc = _lint_json(tmp_path, capsys)
    assert code == 0 and doc["violations"] == [] and doc["summary"]["warnings"] == 1
    [w] = doc["warnings"]
    assert (w["rule"], w["path"], w["value"], w["threshold"]) == ("class-cohesion", "m.py", 2, 1)
    cli.lint.lint(tmp_path, "human")
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("m.py:1:1: WARN class-cohesion ")
    assert out[-1] == "No violations and 1 warning."
    (tmp_path / ".slop.toml").write_text("[rules.class-cohesion]\nenabled = false\n")
    _, off = _lint_json(tmp_path, capsys)
    assert off["warnings"] == []
    code, named = _lint_json(tmp_path, capsys, check=["class-cohesion"])    # `check` runs it anyway
    assert code == 0 and named["warnings"] == doc["warnings"]


def test_doctor_runs(capsys):
    rc = cli.doctor.doctor()
    out = capsys.readouterr().out
    assert "tree-sitter" in out
    assert rc in (0, 2)


def test_ast_default_is_named_skeleton(tmp_path: Path, capsys):
    # The default view drops anonymous tokens (punctuation/keywords): no quoted "def"
    # or "(", but the named structure (function_definition, identifier) is present.
    src = tmp_path / "m.py"
    src.write_text("def add(a, b):\n    return a + b\n")
    assert cli.ast.view(src, "human") == 0
    out = capsys.readouterr().out
    assert "function_definition" in out
    assert "identifier" in out
    assert '"def"' not in out and '"("' not in out
    # IDE-outline surface: the definition shows its name, a line marker, and byte span.
    assert "function_definition  add" in out      # name field surfaced
    assert "L1" in out                            # line numbers
    assert "[0:" in out                           # byte ranges retained


def test_ast_json_carries_lines_and_name(tmp_path: Path, capsys):
    import json
    src = tmp_path / "m.py"
    src.write_text("def add(a, b):\n    return a + b\n")
    assert cli.ast.view(src, "json") == 0
    tree = json.loads(capsys.readouterr().out)
    assert tree["lines"][0] == 1
    fn = next(c for c in tree["children"] if c["type"] == "function_definition")
    assert fn["name"] == "add"
    assert fn["lines"] == [1, 2] and "span" in fn


def test_ast_raw_keeps_anonymous_tokens(tmp_path: Path, capsys):
    src = tmp_path / "m.py"
    src.write_text("def add(a, b):\n    return a + b\n")
    assert cli.ast.view(src, "human", raw=True) == 0
    out = capsys.readouterr().out
    assert '"def"' in out and '"("' in out


def test_ast_json_and_max_depth(tmp_path: Path, capsys):
    import json
    src = tmp_path / "m.py"
    src.write_text("def add(a, b):\n    return a + b\n")
    assert cli.ast.view(src, "json", max_depth=1) == 0
    tree = json.loads(capsys.readouterr().out)
    assert tree["type"] == "module"
    # depth 1 is the deepest emitted; its children are elided with a truncated marker.
    child = tree["children"][0]
    assert child.get("truncated") is True
    assert "children" not in child


def test_ast_errors(tmp_path: Path, capsys):
    assert cli.ast.view(tmp_path / "nope.py", "human") == 2          # missing
    assert cli.ast.view(tmp_path, "human") == 2                       # a directory
    unknown = tmp_path / "x.unknownext"
    unknown.write_text("x")
    assert cli.ast.view(unknown, "human") == 2                       # no grammar


def _mini_pkg(tmp_path: Path) -> Path:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text("import os\n\ndef alpha(value):\n    return os.getpid()\n")
    (pkg / "b.py").write_text("from .a import alpha\n\ndef beta():\n    return alpha(1)\n")
    return tmp_path


def test_lexicon_corpus_and_json(tmp_path: Path, capsys):
    root = _mini_pkg(tmp_path)
    assert cli.lexicon.view(root, "human") == 0
    assert capsys.readouterr().out.startswith("lexicon ")
    import json
    assert cli.lexicon.view(root, "json") == 0
    data = json.loads(capsys.readouterr().out)
    assert data["distinct"] > 0 and "zipf_alpha" in data


def test_lexicon_norm_delta_shown_and_suppressed(tmp_path: Path, capsys):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    # ≥15 distinct identifiers → norm deltas annotated.
    body = "\n".join(f"def func_{i}(arg_{i}):\n    return arg_{i} + {i}" for i in range(20))
    (pkg / "wide.py").write_text(body + "\n")
    (pkg / "tiny.py").write_text("def f():\n    return 1\n")

    assert cli.lexicon.view(tmp_path, "human", scope="pkg/wide.py") == 0
    assert "norm" in capsys.readouterr().out          # deviation annotated

    assert cli.lexicon.view(tmp_path, "human", scope="pkg/tiny.py") == 0
    assert "small sample" in capsys.readouterr().out   # too few tokens; norms suppressed


def test_lexicon_scope_by_path(tmp_path: Path, capsys):
    root = _mini_pkg(tmp_path)
    assert cli.lexicon.view(root, "human", scope="pkg/a.py") == 0
    out = capsys.readouterr().out
    assert "pkg/a.py" in out and "(module)" in out


def test_lexicon_unknown_scope_errors(tmp_path: Path, capsys):
    root = _mini_pkg(tmp_path)
    assert cli.lexicon.view(root, "human", scope="no/such.py") == 2
    assert "no scope" in capsys.readouterr().err


def test_deps_human_and_json(tmp_path: Path, capsys):
    root = _mini_pkg(tmp_path)
    assert cli.deps.view(root, "human") == 0
    out = capsys.readouterr().out
    assert out.startswith("deps ")
    # b imports a — a resolved edge labelled by path
    assert "pkg/b.py" in out and "pkg/a.py" in out
    import json
    assert cli.deps.view(root, "json") == 0
    data = json.loads(capsys.readouterr().out)
    assert data["modules"] >= 2
    assert any(e["from"].endswith("b.py") and (e["to"] or "").endswith("a.py")
               and e["resolved"] for e in data["edges"])


def test_deps_scope_filter(tmp_path: Path, capsys):
    root = _mini_pkg(tmp_path)
    assert cli.deps.view(root, "human", scope="pkg/a.py") == 0
    out = capsys.readouterr().out
    assert "pkg/a.py" in out


def test_deps_unknown_scope_errors(tmp_path: Path, capsys):
    # Parity with lexicon: an unknown --scope is an error (exit 2), not a silent
    # zero-edge result that reads as "no dependencies".
    root = _mini_pkg(tmp_path)
    assert cli.deps.view(root, "human", scope="pkg/nope.py") == 2
    assert "no scope" in capsys.readouterr().err


def test_init_writes_a_template_of_every_rule_and_refuses_to_overwrite(tmp_path: Path, capsys):
    assert cli.config.init(tmp_path) == 0
    cfg = (tmp_path / ".slop.toml").read_text()
    assert "# [rules.cyclomatic-complexity]" in cfg and "# limit = 10" in cfg
    assert "# [rules.duplicate-code]" in cfg and "# min_leaf_nodes = 10" in cfg
    assert "# exclude" in cfg
    assert cli.config.init(tmp_path) == 2


def test_lint_and_check_drop_excluded_files(tmp_path: Path, capsys):
    # tests/ holds the only branchy function; with threshold 2 it is a violation until the
    # config excludes tests/**. Valid config (no stale rule), so this exercises `load`.
    (tmp_path / "app.py").write_text("def ok(x):\n    return x\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text(
        "def branchy(x):\n    if x:\n        return 1\n    if x > 2:\n        return 2\n    return 3\n")
    rule = "[rules.cyclomatic-complexity]\nlimit = 2\n"

    def paths(check: list[str] | None = None) -> set[str]:
        return {v["path"] for v in _lint_json(tmp_path, capsys, check=check)[1]["violations"]}

    (tmp_path / ".slop.toml").write_text(rule)
    assert paths() == {"tests/test_a.py"}
    assert paths(["cyclomatic-complexity"]) == {"tests/test_a.py"}

    (tmp_path / ".slop.toml").write_text('exclude = ["tests/**"]\n' + rule)
    assert paths() == set()
    assert paths(["cyclomatic-complexity"]) == set()


_BRANCHY = "def f(v):\n    if v:\n        return 1\n    if v > 2:\n        return 2\n    return 3\n"
_LOW = "[rules.cyclomatic-complexity]\nlimit = 2\n"


def _lint_json(root: Path, capsys, *, check: list[str] | None = None) -> tuple[int, dict]:
    capsys.readouterr()
    code = cli.lint.check(check, root, "json") if check else cli.lint.lint(root, "json")
    return code, json.loads(capsys.readouterr().out)


def _cyclomatic_paths(root: Path, capsys) -> set[str]:
    _, doc = _lint_json(root, capsys)
    return {v["path"] for v in doc["violations"] if v["rule"] == "cyclomatic-complexity"}


def test_same_named_functions_in_two_files_are_both_reported_at_their_own_paths(tmp_path: Path, capsys):
    # `a/x.py:f` and `b/x.py:f` are both `x.f`; each violation must carry its own file.
    for pkg in ("a", "b"):
        (tmp_path / pkg).mkdir()
        (tmp_path / pkg / "__init__.py").write_text("")
        (tmp_path / pkg / "x.py").write_text(_BRANCHY)
    (tmp_path / ".slop.toml").write_text(_LOW)
    assert _cyclomatic_paths(tmp_path, capsys) == {"a/x.py", "b/x.py"}


def test_an_ignore_table_is_now_a_config_error(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(_BRANCHY)
    (tmp_path / ".slop.toml").write_text(_LOW + '[ignore]\nfunctions = ["f"]\n')
    assert cli.main(["lint", "--root", str(tmp_path)]) == 2
    err = capsys.readouterr().err
    assert "unknown key" in err and "ignore" in err
    assert cli.main(["check", "cyclomatic-complexity", "--root", str(tmp_path)]) == 2


def test_an_inline_ignore_comment_exempts_only_its_own_function(tmp_path: Path, capsys):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "x.py").write_text(_BRANCHY.replace("def f(v):", "def f(v):  # slop: ignore"))
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "x.py").write_text(_BRANCHY)
    (tmp_path / ".slop.toml").write_text(_LOW)
    assert _cyclomatic_paths(tmp_path, capsys) == {"b/x.py"}


def _leaf_commands(parser, path=()):
    """Every runnable command: a parser with no subcommands, by its path of names."""
    import argparse
    groups = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
    if not groups:
        yield path, parser
        return
    for name, child in groups[0].choices.items():
        yield from _leaf_commands(child, (*path, name))


def test_every_command_has_a_handler():
    leaves = dict(_leaf_commands(cli.parser()))
    assert {("lint",), ("doctor",), ("infer", "apply"), ("skill", "install")} <= set(leaves)
    missing = [" ".join(path) for path, parser in leaves.items() if not callable(parser.get_default("run"))]
    assert missing == []


def test_a_command_runs_its_own_handler(capsys):
    assert cli.main(["skill", "list"]) == 0 and capsys.readouterr().out.startswith("slop")
    assert cli.main(["doctor"]) == 0 and "tree-sitter" in capsys.readouterr().out


_WIRING = [
    (["lint", "--root", "r", "--output", "json"], "lint.lint", ("r", "json"), {}),
    (["check", "a", "b", "--root", "r"], "lint.check", (["a", "b"], "r", "human"), {}),
    (["rules", "--output", "json"], "lint.rules", ("json",), {}),
    (["doctor"], "doctor.doctor", (), {}),
    (["init", "--root", "r"], "config.init", ("r",), {}),
    (["ast", "f.py", "--raw", "--max-depth", "3"], "ast.view", ("f.py", "human"), {"raw": True, "max_depth": 3}),
    (["lexicon", "--root", "r", "--scope", "s", "--top", "5", "--scope-kind", "module", "--ontology", "o.json"],
     "lexicon.view", ("r", "human"), {"scope": "s", "top": 5, "scope_kind": "module", "ontology": "o.json"}),
    (["deps", "--root", "r", "--scope", "s", "--cycles"], "deps.view", ("r", "human"), {"scope": "s", "cycles_only": True}),
    (["find", "N", "--root", "r", "--kind", "class", "--collisions"], "find.view", ("r", "N", "human"),
     {"kind": "class", "collisions": True}),
    (["tree", "--root", "r", "--scope", "s", "--depth", "2", "--kind", "class", "--scope-kind", "package"], "tree.view",
     ("r", "human"), {"scope": "s", "depth": 2, "kind": "class", "scope_kind": "package"}),
    (["vocab", "--ontology", "o.json", "--root", "r", "--term", "T"], "ontology.vocab", ("r", "o.json", "human"), {"term": "T"}),
    (["shape", "--root", "r", "--scope", "s", "--scope-kind", "class"], "shape.view", ("r", "human"),
     {"scope": "s", "scope_kind": "class"}),
    (["hotspots", "--root", "r", "--since", "HEAD~3"], "hotspots.view", ("r", "human"), {"since": "HEAD~3", "last": None}),
    (["infer", "instructions"], "infer.instructions", (), {}),
    (["infer", "references", "rubrics/x"], "infer.references", ("rubrics/x",), {}),
    (["infer", "schema", "verdicts"], "infer.schema", ("verdicts",), {}),
    (["infer", "apply", "v.json", "--root", "r"], "infer.apply", ("v.json", "r"), {}),
    (["ontology", "draft", "--root", "r", "--force"], "ontology.draft", ("r", True), {}),
    (["ontology", "check", "--root", "r"], "ontology.check", ("r",), {}),
    (["skill", "list"], "skill.catalog", (), {}),
    (["skill", "show", "slop", "SKILL.md"], "skill.show", ("slop", "SKILL.md"), {}),
    (["skill", "install", "slop", "--dest", "d", "--force"], "skill.install", ("slop", "d", True), {}),
]


@pytest.mark.parametrize("argv,handler,args,kwargs", _WIRING, ids=[" ".join(w[0][:2]) for w in _WIRING])
def test_each_command_reaches_its_handler_with_its_arguments(monkeypatch, argv, handler, args, kwargs):
    calls = []
    module, function = handler.split(".")
    monkeypatch.setattr(getattr(cli, module), function, lambda *a, **k: calls.append((a, k)) or 0)
    assert cli.main(argv) == 0
    assert calls == [(args, kwargs)]


def test_the_wiring_table_covers_every_command():
    covered = {tuple(argv[:2]) if argv[0] in ("infer", "ontology", "skill") else (argv[0],) for argv, *_ in _WIRING}
    assert covered == set(dict(_leaf_commands(cli.parser())))
