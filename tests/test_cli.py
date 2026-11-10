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
    assert cli._version() in out


def test_version_helper_resolves_installed_distribution():
    # The package is installed (editable) in the dev env, so metadata resolves to a
    # real version rather than the source-tree "unknown" fallback.
    assert cli._version() != "unknown"


def test_rules_lists_registry(capsys):
    rc = cli.rules_cmd("human")
    out = capsys.readouterr().out
    assert rc == 0
    assert "complexity.cyclomatic" in out
    assert "rules" in out


def test_rules_json(capsys):
    rc = cli.rules_cmd("json")
    data = json.loads(capsys.readouterr().out)
    assert rc == 0
    by_name = {r["name"]: r for r in data}
    assert "complexity.cyclomatic" in by_name and "class.coupling" in by_name
    assert not {"orphans", "hotspots", "vocabulary", "class-shape"} & set(by_name)
    assert by_name["class.cohesion"]["enabled"] is False
    assert by_name["complexity.cyclomatic"]["altitudes"] == ["callable"]


def test_rules_human_marks_default_off_rules(capsys):
    cli.rules_cmd("human")
    lines = capsys.readouterr().out.splitlines()
    [cohesion] = [ln for ln in lines if "class.cohesion" in ln]
    [cyclomatic] = [ln for ln in lines if "complexity.cyclomatic" in ln]
    assert " off " in cohesion and " on " in cyclomatic


def test_schema_json_is_v2(capsys):
    assert cli.schema_cmd("json") == 0
    data = json.loads(capsys.readouterr().out)
    assert data["version"] == "v2" and {"exclude", "languages", "rules"} <= set(data)
    cohesion = next(r for r in data["rules"] if r["name"] == "class.cohesion")
    assert cohesion["enabled"] is False and cohesion["thresholds"] == {"class": 1}


def test_check_unknown_target_errors(capsys):
    assert cli.check("nonsense.rule", ".", "human") == 2


def test_a_name_that_only_prefixes_a_rule_is_not_a_family(capsys):
    assert cli.check("complex", ".", "human") == 2


def test_nonexistent_root_errors(tmp_path: Path, capsys):
    # A missing root must error (exit 2), not report "clean": the CLI-boundary form
    # of "not-flagged != clean".
    missing = tmp_path / "does-not-exist"
    assert cli.lint(missing, "human") == 2
    assert "does not exist" in capsys.readouterr().err


def test_empty_root_errors(tmp_path: Path, capsys):
    # An existing root with no source files would visit zero components and read as
    # clean; that is a false pass, so it errors.
    (tmp_path / "notes.txt").write_text("not source\n")
    assert cli.lint(tmp_path, "human") == 2
    assert "no source files" in capsys.readouterr().err


_TANGLED = "def f(a, b):\n" + "".join(f"    if a == {i}: b += {i}\n" for i in range(15)) + "    return b\n"


def test_lint_human_output_is_one_located_line_per_violation(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(_TANGLED)
    assert cli.lint(tmp_path, "human") == 1
    lines = capsys.readouterr().out.splitlines()
    cyclomatic = [ln for ln in lines if " complexity.cyclomatic " in ln]
    assert len(cyclomatic) == 1
    assert cyclomatic[0].startswith("m.py:1:1: complexity.cyclomatic ")
    assert "16" in cyclomatic[0] and "limit 10" in cyclomatic[0]
    assert lines[-1] == f"Found {len(lines) - 1} violations."


def test_lint_human_output_uses_the_singular_for_one_violation(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(_BRANCHY)
    (tmp_path / ".slop.toml").write_text(_LOW)
    assert cli.lint(tmp_path, "human") == 1
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 2 and lines[0].startswith("m.py:1:1: complexity.cyclomatic ")
    assert lines[1] == "Found 1 violation."


def test_lint_clean_source_exits_zero_with_no_violations(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text("def f(x):\n    return x\n")
    assert cli.lint(tmp_path, "human") == 0
    assert capsys.readouterr().out.strip() == "No violations."


def test_lint_json_shape(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(_TANGLED)
    code, doc = _lint_json(tmp_path, capsys)
    assert code == 1 and set(doc) == {"summary", "violations", "zero_visited"}
    assert doc["summary"] == {"violations": len(doc["violations"]), "exit_code": 1}
    assert "findings" not in doc
    v = next(v for v in doc["violations"] if v["rule"] == "complexity.cyclomatic")
    assert v == {"rule": "complexity.cyclomatic", "path": "m.py", "line": 1, "column": 1,
                 "message": v["message"], "value": 16, "threshold": 10}


def test_lint_json_of_clean_source(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text("def f(x):\n    return x\n")
    code, doc = _lint_json(tmp_path, capsys)
    assert code == 0 and doc["violations"] == [] and doc["summary"] == {"violations": 0, "exit_code": 0}


def test_check_filters_to_a_family(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(_TANGLED)
    code, doc = _lint_json(tmp_path, capsys, check="complexity")
    assert code == 1
    fired = {v["rule"] for v in doc["violations"]}
    assert "complexity.cyclomatic" in fired and all(r.startswith("complexity.") for r in fired)


def test_check_filters_to_one_rule(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(_TANGLED)
    code, doc = _lint_json(tmp_path, capsys, check="complexity.cyclomatic")
    assert code == 1 and {v["rule"] for v in doc["violations"]} == {"complexity.cyclomatic"}


def test_check_exits_zero_when_its_rules_are_clean_though_others_are_not(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(_TANGLED)
    code, doc = _lint_json(tmp_path, capsys, check="structure")
    assert code == 0 and doc["violations"] == []


def test_check_with_ancestor_config_for_other_rule(tmp_path: Path, capsys):
    # A config that configures a rule OUTSIDE the checked subset must not make
    # `check` raise "configures unknown rule" (regression: validate against the
    # full registry, dispatch only the subset).
    (tmp_path / ".slop.toml").write_text('[rules."structure.god-module"]\nenabled = false\n')
    (tmp_path / "m.py").write_text("def f(x): return x\n")
    assert cli.check("complexity", tmp_path, "json") == 0


def test_an_invalid_config_is_exit_two_not_a_clean_run(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(_TANGLED)
    (tmp_path / ".slop.toml").write_text('[rules."complexity.cyclomatic"]\nseverity = "warning"\n')
    assert cli.main(["lint", "--root", str(tmp_path)]) == 2
    assert "severity" in capsys.readouterr().err


def test_a_disabled_rule_reports_nothing(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(_TANGLED)
    (tmp_path / ".slop.toml").write_text('[rules."complexity.cyclomatic"]\nenabled = false\n')
    _, doc = _lint_json(tmp_path, capsys)
    assert "complexity.cyclomatic" not in {v["rule"] for v in doc["violations"]}


def test_class_cohesion_is_reported_once_enabled(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(
        "class A:\n    def f(self): return self.a\n    def g(self): return self.b\n")
    _, doc = _lint_json(tmp_path, capsys)
    assert doc["violations"] == []
    (tmp_path / ".slop.toml").write_text('[rules."class.cohesion"]\nenabled = true\n')
    _, doc = _lint_json(tmp_path, capsys)
    [v] = doc["violations"]
    assert (v["rule"], v["path"], v["value"], v["threshold"]) == ("class.cohesion", "m.py", 2, 1)


def test_doctor_runs(capsys):
    rc = cli.doctor()
    out = capsys.readouterr().out
    assert "tree-sitter" in out
    assert rc in (0, 2)


def test_ast_default_is_named_skeleton(tmp_path: Path, capsys):
    # The default view drops anonymous tokens (punctuation/keywords): no quoted "def"
    # or "(", but the named structure (function_definition, identifier) is present.
    src = tmp_path / "m.py"
    src.write_text("def add(a, b):\n    return a + b\n")
    assert cli.ast_view(src, "human") == 0
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
    assert cli.ast_view(src, "json") == 0
    tree = json.loads(capsys.readouterr().out)
    assert tree["lines"][0] == 1
    fn = next(c for c in tree["children"] if c["type"] == "function_definition")
    assert fn["name"] == "add"
    assert fn["lines"] == [1, 2] and "span" in fn


def test_ast_raw_keeps_anonymous_tokens(tmp_path: Path, capsys):
    src = tmp_path / "m.py"
    src.write_text("def add(a, b):\n    return a + b\n")
    assert cli.ast_view(src, "human", raw=True) == 0
    out = capsys.readouterr().out
    assert '"def"' in out and '"("' in out


def test_ast_json_and_max_depth(tmp_path: Path, capsys):
    import json
    src = tmp_path / "m.py"
    src.write_text("def add(a, b):\n    return a + b\n")
    assert cli.ast_view(src, "json", max_depth=1) == 0
    tree = json.loads(capsys.readouterr().out)
    assert tree["type"] == "module"
    # depth 1 is the deepest emitted; its children are elided with a truncated marker.
    child = tree["children"][0]
    assert child.get("truncated") is True
    assert "children" not in child


def test_ast_errors(tmp_path: Path, capsys):
    assert cli.ast_view(tmp_path / "nope.py", "human") == 2          # missing
    assert cli.ast_view(tmp_path, "human") == 2                       # a directory
    unknown = tmp_path / "x.unknownext"
    unknown.write_text("x")
    assert cli.ast_view(unknown, "human") == 2                       # no grammar


def _mini_pkg(tmp_path: Path) -> Path:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text("import os\n\ndef alpha(value):\n    return os.getpid()\n")
    (pkg / "b.py").write_text("from .a import alpha\n\ndef beta():\n    return alpha(1)\n")
    return tmp_path


def test_lexicon_corpus_and_json(tmp_path: Path, capsys):
    root = _mini_pkg(tmp_path)
    assert cli.lexicon_view(root, "human") == 0
    assert capsys.readouterr().out.startswith("lexicon ")
    import json
    assert cli.lexicon_view(root, "json") == 0
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

    assert cli.lexicon_view(tmp_path, "human", scope="pkg/wide.py") == 0
    assert "norm" in capsys.readouterr().out          # deviation annotated

    assert cli.lexicon_view(tmp_path, "human", scope="pkg/tiny.py") == 0
    assert "small sample" in capsys.readouterr().out   # too few tokens; norms suppressed


def test_lexicon_scope_by_path(tmp_path: Path, capsys):
    root = _mini_pkg(tmp_path)
    assert cli.lexicon_view(root, "human", scope="pkg/a.py") == 0
    out = capsys.readouterr().out
    assert "pkg/a.py" in out and "(module)" in out


def test_lexicon_unknown_scope_errors(tmp_path: Path, capsys):
    root = _mini_pkg(tmp_path)
    assert cli.lexicon_view(root, "human", scope="no/such.py") == 2
    assert "no scope" in capsys.readouterr().err


def test_deps_human_and_json(tmp_path: Path, capsys):
    root = _mini_pkg(tmp_path)
    assert cli.deps_view(root, "human") == 0
    out = capsys.readouterr().out
    assert out.startswith("deps ")
    # b imports a — a resolved edge labelled by path
    assert "pkg/b.py" in out and "pkg/a.py" in out
    import json
    assert cli.deps_view(root, "json") == 0
    data = json.loads(capsys.readouterr().out)
    assert data["modules"] >= 2
    assert any(e["from"].endswith("b.py") and (e["to"] or "").endswith("a.py")
               and e["resolved"] for e in data["edges"])


def test_deps_scope_filter(tmp_path: Path, capsys):
    root = _mini_pkg(tmp_path)
    assert cli.deps_view(root, "human", scope="pkg/a.py") == 0
    out = capsys.readouterr().out
    assert "pkg/a.py" in out


def test_deps_unknown_scope_errors(tmp_path: Path, capsys):
    # Parity with lexicon: an unknown --scope is an error (exit 2), not a silent
    # zero-edge result that reads as "no dependencies".
    root = _mini_pkg(tmp_path)
    assert cli.deps_view(root, "human", scope="pkg/nope.py") == 2
    assert "no scope" in capsys.readouterr().err


def test_init_writes_template(tmp_path: Path, capsys):
    assert cli.init(tmp_path) == 0
    cfg = (tmp_path / ".slop.toml").read_text()
    assert '[rules."complexity.cyclomatic"]' in cfg
    assert "thresholds.callable = 10" in cfg
    assert "# exclude" in cfg and "# languages" in cfg
    assert "severity" not in cfg and "ignore" not in cfg.replace("slop: ignore", "")
    # second init refuses to overwrite
    assert cli.init(tmp_path) == 2


def test_lint_and_check_drop_excluded_files(tmp_path: Path, capsys):
    # tests/ holds the only branchy function; with threshold 2 it is a violation until the
    # config excludes tests/**. Valid config (no stale rule), so this exercises `load`.
    (tmp_path / "app.py").write_text("def ok(x):\n    return x\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text(
        "def branchy(x):\n    if x:\n        return 1\n    if x > 2:\n        return 2\n    return 3\n")
    rule = '[rules."complexity.cyclomatic".thresholds]\ncallable = 2\n'

    def paths(check: str | None = None) -> set[str]:
        return {v["path"] for v in _lint_json(tmp_path, capsys, check=check)[1]["violations"]}

    (tmp_path / ".slop.toml").write_text(rule)
    assert paths() == {"tests/test_a.py"}
    assert paths("complexity.cyclomatic") == {"tests/test_a.py"}

    (tmp_path / ".slop.toml").write_text('exclude = ["tests/**"]\n' + rule)
    assert paths() == set()
    assert paths("complexity.cyclomatic") == set()


_BRANCHY = "def f(v):\n    if v:\n        return 1\n    if v > 2:\n        return 2\n    return 3\n"
_LOW = '[rules."complexity.cyclomatic".thresholds]\ncallable = 2\n'


def _lint_json(root: Path, capsys, *, check: str | None = None) -> tuple[int, dict]:
    capsys.readouterr()
    code = cli.check(check, root, "json") if check else cli.lint(root, "json")
    return code, json.loads(capsys.readouterr().out)


def _cyclomatic_paths(root: Path, capsys) -> set[str]:
    _, doc = _lint_json(root, capsys)
    return {v["path"] for v in doc["violations"] if v["rule"] == "complexity.cyclomatic"}


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
    assert cli.main(["check", "complexity", "--root", str(tmp_path)]) == 2


def test_an_inline_ignore_comment_exempts_only_its_own_function(tmp_path: Path, capsys):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "x.py").write_text(_BRANCHY.replace("def f(v):", "def f(v):  # slop: ignore"))
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "x.py").write_text(_BRANCHY)
    (tmp_path / ".slop.toml").write_text(_LOW)
    assert _cyclomatic_paths(tmp_path, capsys) == {"b/x.py"}
