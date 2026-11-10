"""CLI subcommands — rules / check / doctor / init (plus the existing lint)."""
from __future__ import annotations

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
    out = capsys.readouterr().out
    assert rc == 0
    import json
    data = json.loads(out)
    names = {r["name"] for r in data}
    assert "complexity.cyclomatic" in names and "orphans" in names


def test_check_unknown_target_errors(capsys):
    assert cli.check("nonsense.rule", ".", "human") == 2


def test_nonexistent_root_errors(tmp_path: Path, capsys):
    # A missing root must error (exit 2), not report "clean" — the CLI-boundary form
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


def test_check_filters_to_family(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(
        "def f(a, b):\n" + "".join(f"    if a == {i}: b += {i}\n" for i in range(15)) + "    return b\n"
    )
    assert cli.check("complexity", tmp_path, "json") in (0, 1)
    out = capsys.readouterr().out
    import json
    data = json.loads(out)
    rules_fired = {f["rule"] for f in data["findings"]} if data.get("findings") else set()
    assert all(r.startswith("complexity.") for r in rules_fired)


def test_check_with_ancestor_config_for_other_rule(tmp_path: Path, capsys):
    # A config that configures a rule OUTSIDE the checked subset must not make
    # `check` raise "configures unknown rule" (regression: validate against the
    # full registry, dispatch only the subset).
    (tmp_path / ".slop.toml").write_text('[rules."structure.god-module"]\nenabled = false\n')
    (tmp_path / "m.py").write_text("def f(x): return x\n")
    rc = cli.check("complexity", tmp_path, "json")
    assert rc in (0, 1)  # ran cleanly, did not error (2)


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
    assert "[rules." in cfg
    # second init refuses to overwrite
    assert cli.init(tmp_path) == 2


def test_lint_and_check_drop_excluded_files(tmp_path: Path, capsys):
    # tests/ holds the only branchy function; with threshold 1 it is a finding until the
    # config excludes tests/**. Valid config (no stale rule), so this exercises `load`.
    import json
    (tmp_path / "app.py").write_text("def ok(x):\n    return x\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text(
        "def branchy(x):\n    if x:\n        return 1\n    if x > 2:\n        return 2\n    return 3\n")
    rule = '[rules."complexity.cyclomatic".thresholds]\ncallable = 2\n'

    def findings(run) -> set[str]:
        capsys.readouterr()
        run()
        return {f["path"] for f in json.loads(capsys.readouterr().out)["findings"]}

    (tmp_path / ".slop.toml").write_text(rule)
    assert findings(lambda: cli.lint(tmp_path, "json")) == {"tests/test_a.py"}
    assert findings(lambda: cli.check("complexity.cyclomatic", tmp_path, "json")) == {"tests/test_a.py"}

    (tmp_path / ".slop.toml").write_text('exclude = ["tests/**"]\n' + rule)
    assert findings(lambda: cli.lint(tmp_path, "json")) == set()
    assert findings(lambda: cli.check("complexity.cyclomatic", tmp_path, "json")) == set()


_BRANCHY = "def f(v):\n    if v:\n        return 1\n    if v > 2:\n        return 2\n    return 3\n"


def _cyclomatic_paths(root: Path, capsys) -> set[str]:
    import json
    cli.lint(root, "json")
    findings = json.loads(capsys.readouterr().out)["findings"]
    return {f["path"] for f in findings if f["rule"] == "complexity.cyclomatic"}


def _two_same_named_branchy_functions(root: Path, ignore: str) -> None:
    """`a/x.py:f` and `b/x.py:f` are both `x.f` and both over the cyclomatic threshold."""
    for pkg in ("a", "b"):
        (root / pkg).mkdir()
        (root / pkg / "__init__.py").write_text("")
        (root / pkg / "x.py").write_text(_BRANCHY)
    (root / ".slop.toml").write_text(
        '[rules."complexity.cyclomatic".thresholds]\ncallable = 2\n' + ignore)


def test_without_an_ignore_both_same_named_functions_are_flagged(tmp_path: Path, capsys):
    _two_same_named_branchy_functions(tmp_path, "")
    assert _cyclomatic_paths(tmp_path, capsys) == {"a/x.py", "b/x.py"}


def test_a_plain_ignore_entry_exempts_every_unit_of_that_name(tmp_path: Path, capsys):
    _two_same_named_branchy_functions(tmp_path, '[ignore]\nfunctions = ["f"]\n')
    assert _cyclomatic_paths(tmp_path, capsys) == set()


def test_a_path_qualified_ignore_entry_exempts_only_that_file(tmp_path: Path, capsys):
    _two_same_named_branchy_functions(tmp_path, '[ignore]\nfunctions = ["a/x.py::f"]\n')
    assert _cyclomatic_paths(tmp_path, capsys) == {"b/x.py"}


def test_ignore_path_matches_at_a_directory_boundary(tmp_path: Path, capsys):
    # "x.py" must not exempt a file called "ax.py"; the path matches whole segments.
    (tmp_path / "ax.py").write_text(_BRANCHY)
    (tmp_path / ".slop.toml").write_text(
        '[rules."complexity.cyclomatic".thresholds]\ncallable = 2\n[ignore]\nfunctions = ["x.py::f"]\n')
    assert _cyclomatic_paths(tmp_path, capsys) == {"ax.py"}
