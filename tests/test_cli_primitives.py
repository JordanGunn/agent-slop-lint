"""The primitive commands, driven only through the CLI.

Each test asks the question an agent would ask and checks the answer from the JSON
output alone: no thresholds, no judgment. If an agent can answer these from returned
facts, the primitives are dependable enough to infer from.

Exit contract for primitives: 0 whenever the question was answered (an empty result is
an answer), 2 when it could not be.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from slop import cli

IR = str(Path(__file__).parent / "fixtures" / "support_desk.ir.json")


def _ask(capsys, *argv: str) -> tuple[int, dict | str, str]:
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    out = captured.out
    try:
        return code, json.loads(out), captured.err
    except json.JSONDecodeError:
        return code, out, captured.err


# ---- Q1: where is X defined? ----------------------------------------------

def test_where_is_a_name_defined(sample_project: Path, capsys):
    code, answer, _ = _ask(capsys, "find", "Address", "--root", str(sample_project), "--output", "json")
    assert code == 0
    assert answer["matches"] == [
        {"kind": "class", "name": "Address", "qualname": "address.Address",
         "path": "store/address.py", "line": 1},
    ]


def test_a_name_defined_nowhere_is_an_answer_not_an_error(sample_project: Path, capsys):
    code, answer, _ = _ask(capsys, "find", "Nowhere", "--root", str(sample_project), "--output", "json")
    assert code == 0 and answer["matches"] == []


def test_human_output_names_the_location(sample_project: Path, capsys):
    code, text, _ = _ask(capsys, "find", "Store", "--root", str(sample_project))
    assert code == 0
    assert "store/array.py:1" in text and "store/frame.py:1" in text


def test_discovery_is_language_agnostic(tmp_path: Path, capsys):
    # The same word defined in four languages is found with a path and line in each, and
    # reported as one collision: the primitives read the ownership tree, not one grammar.
    (tmp_path / "go").mkdir()
    (tmp_path / "go" / "go.mod").write_text("module example.com/x\ngo 1.21\n")
    (tmp_path / "go" / "store.go").write_text("package store\n\ntype Store struct {\n\tpath string\n}\n")
    (tmp_path / "ts").mkdir()
    (tmp_path / "ts" / "store.ts").write_text("export class Store {\n  save(): number { return 1; }\n}\n")
    (tmp_path / "rs").mkdir()
    (tmp_path / "rs" / "store.rs").write_text("pub struct Store { pub path: String }\n")
    (tmp_path / "py").mkdir()
    (tmp_path / "py" / "store.py").write_text("class Store:\n    pass\n")
    _, answer, _ = _ask(capsys, "find", "Store", "--kind", "class", "--root", str(tmp_path), "--output", "json")
    assert [(m["path"], m["line"]) for m in answer["matches"]] == [
        ("go/store.go", 3), ("py/store.py", 1), ("rs/store.rs", 1), ("ts/store.ts", 1),
    ]
    _, collisions, _ = _ask(capsys, "find", "--collisions", "--root", str(tmp_path), "--output", "json")
    assert set(collisions["collisions"]) == {"Store"}


# ---- Q2: what is in package Y? --------------------------------------------

def test_what_a_package_holds(sample_project: Path, capsys):
    code, answer, _ = _ask(capsys, "tree", "--root", str(sample_project), "--scope", "store",
                           "--scope-kind", "package", "--kind", "class", "--output", "json")
    assert code == 0
    assert answer["kind"] == "package"
    assert sorted((r["name"], r["path"]) for r in answer["rows"]) == [
        ("Address", "store/address.py"), ("Store", "store/array.py"), ("Store", "store/frame.py"),
    ]


def test_a_package_and_its_init_module_are_told_apart_not_guessed(sample_project: Path, capsys):
    # 'store' names both the package and store/__init__.py. Picking one silently would
    # be a heuristic; the error lists both kinds and the flag that resolves it.
    code = cli.main(["tree", "--root", str(sample_project), "--scope", "store"])
    err = capsys.readouterr().err
    assert code == 2
    assert "ambiguous" in err and "--scope-kind" in err
    assert "package" in err and "module" in err
    assert cli.main(["tree", "--root", str(sample_project), "--scope", "store",
                     "--scope-kind", "module"]) == 0


def test_lexicon_takes_the_same_scope_kind_selector(sample_project: Path, capsys):
    assert cli.main(["lexicon", "--root", str(sample_project), "--scope", "store"]) == 2
    capsys.readouterr()
    code, answer, _ = _ask(capsys, "lexicon", "--root", str(sample_project), "--scope", "store",
                           "--scope-kind", "package", "--output", "json")
    assert code == 0 and answer["kind"] == "package"


def test_tree_depth_limits_levels(sample_project: Path, capsys):
    _, deep, _ = _ask(capsys, "tree", "--root", str(sample_project), "--output", "json")
    _, shallow, _ = _ask(capsys, "tree", "--root", str(sample_project), "--depth", "1", "--output", "json")
    assert len(shallow["rows"]) < len(deep["rows"])
    assert {r["level"] for r in shallow["rows"]} == {1}


# ---- Q3: which names collide? ---------------------------------------------

def test_which_names_are_defined_more_than_once(sample_project: Path, capsys):
    code, answer, _ = _ask(capsys, "find", "--collisions", "--root", str(sample_project), "--output", "json")
    assert code == 0
    assert answer["kind"] == "class"
    assert set(answer["collisions"]) == {"Index", "Store", "Twin"}
    assert {m["path"] for m in answer["collisions"]["Index"]} == {"index/octree.py", "index/quadtree.py"}


# ---- Q4: what is the canonical term for Z? --------------------------------

def test_what_a_word_means_canonically(capsys):
    code, answer, _ = _ask(capsys, "vocab", "--ontology", IR, "--term", "customer", "--output", "json")
    assert code == 0
    assert answer["canonical"]["name"] == "Customer"
    assert answer["canonical"]["description"] == "An organisation that raises tickets."
    assert answer["canonical"]["kind"] == "entity"


def test_a_non_canonical_word_is_an_answer_not_an_error(capsys):
    code, answer, _ = _ask(capsys, "vocab", "--ontology", IR, "--term", "Bogus", "--output", "json")
    assert code == 0 and answer["canonical"] is None


def test_code_names_against_the_ontology(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(
        "class Ticket:\n    pass\n\nclass Customer:\n    pass\n\nclass TicketManager:\n    pass\n")
    code, answer, _ = _ask(capsys, "vocab", "--ontology", IR, "--root", str(tmp_path), "--output", "json")
    assert code == 0
    assert [m["term"] for m in answer["matched"]] == ["Customer", "Ticket"]
    assert [m["name"] for m in answer["unknown"]] == ["TicketManager"]   # a near miss is not a match
    assert answer["unused"] == ["Engineer"]


# ---- the primitives fail loudly -------------------------------------------

@pytest.mark.parametrize("argv,fragment", [
    (["find"], "needs a NAME"),
    (["find", "X", "--kind", "banana"], "unknown kind"),
    (["vocab", "--ontology", "/nonexistent/ir.json", "--term", "x"], "cannot read ontology"),
])
def test_unanswerable_questions_exit_2_with_a_reason(capsys, tmp_path: Path, argv, fragment):
    (tmp_path / "m.py").write_text("class A:\n    pass\n")
    code = cli.main([*argv, "--root", str(tmp_path)] if argv[0] != "vocab" else argv)
    assert code == 2
    assert fragment in capsys.readouterr().err


def test_a_source_free_root_is_an_error_not_an_empty_answer(tmp_path: Path, capsys):
    # 'no match' over zero source would read as a clean answer; it must not.
    code = cli.main(["find", "X", "--root", str(tmp_path)])
    assert code == 2
    assert "no source files" in capsys.readouterr().err


def test_a_root_with_no_classes_cannot_be_compared(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text("def only_a_function():\n    return 1\n")
    code = cli.main(["vocab", "--ontology", IR, "--root", str(tmp_path)])
    assert code == 2
    assert "vacuous" in capsys.readouterr().err


def test_a_file_that_is_not_an_ontology_is_rejected(tmp_path: Path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text('{"kind": "nope"}')
    assert cli.main(["vocab", "--ontology", str(bad), "--term", "x"]) == 2
    assert "not an Open Ontology IR" in capsys.readouterr().err


# ---- determinism ----------------------------------------------------------

def test_two_runs_print_identical_bytes(sample_project: Path, capsys):
    outputs = []
    for _ in range(2):
        cli.main(["find", "--collisions", "--root", str(sample_project), "--output", "json"])
        cli.main(["tree", "--root", str(sample_project), "--output", "json"])
        outputs.append(capsys.readouterr().out)
    assert outputs[0] == outputs[1]


# ---- every grammar either answers or says it cannot ------------------------

_WIDGET = {
    "m.py": "class Widget:\n    pass\n",
    "m.js": "class Widget {}\n",
    "m.ts": "export class Widget {}\n",
    "m.go": "package m\n\ntype Widget struct{}\n",
    "Widget.java": "public class Widget {}\n",
    "Widget.cs": "public class Widget {}\n",
    "m.rs": "pub struct Widget {}\n",
    "m.cpp": "class Widget {};\n",
    "m.rb": "class Widget\nend\n",
    "m.c": "struct Widget { int x; };\n",
    "m.jl": "struct Widget\nend\n",
}


@pytest.mark.parametrize("filename", sorted(_WIDGET))
def test_class_bearing_grammars_find_a_defined_class(tmp_path: Path, capsys, filename: str):
    (tmp_path / filename).write_text(_WIDGET[filename])
    if filename.endswith(".go"):
        (tmp_path / "go.mod").write_text("module example.com/m\ngo 1.21\n")
    _, answer, _ = _ask(capsys, "find", "Widget", "--kind", "class", "--root", str(tmp_path),
                        "--output", "json")
    assert [m["name"] for m in answer["matches"]] == ["Widget"]
    assert answer["caveats"] == []


def test_vocab_matches_a_c_struct_against_the_ontology(tmp_path: Path, capsys):
    (tmp_path / "a.py").write_text("class Ticket:\n    pass\n")
    (tmp_path / "b.c").write_text("struct Customer { int x; };\n")
    _, answer, _ = _ask(capsys, "vocab", "--ontology", IR, "--root", str(tmp_path), "--output", "json")
    assert [m["term"] for m in answer["matched"]] == ["Customer", "Ticket"]
    assert answer["caveats"] == []


def _polyglot(tmp_path: Path) -> None:
    # A clean Python realm beside a C realm with a syntax error (a struct missing its brace).
    (tmp_path / "p").mkdir()
    (tmp_path / "p" / "a.py").write_text("class Widget:\n    pass\n")
    (tmp_path / "c").mkdir()
    (tmp_path / "c" / "b.c").write_text("struct Widget { int x;\n")


def test_a_tree_scoped_to_one_realm_carries_only_that_realms_caveats(tmp_path: Path, capsys):
    # The C realm's broken file cannot affect rows under the Python realm.
    _polyglot(tmp_path)
    _, whole, _ = _ask(capsys, "tree", "--root", str(tmp_path), "--output", "json")
    _, py_only, _ = _ask(capsys, "tree", "--root", str(tmp_path), "--scope", "python",
                         "--scope-kind", "realm", "--output", "json")
    assert any("b.c" in c for c in whole["caveats"])
    assert py_only["caveats"] == []


def test_syntax_error_notes_apply_to_every_kind_of_question(tmp_path: Path, capsys):
    _polyglot(tmp_path)
    for kind in ("class", "callable"):
        _, answer, _ = _ask(capsys, "find", "Widget", "--kind", kind, "--root", str(tmp_path),
                            "--output", "json")
        assert len(answer["caveats"]) == 1 and "b.c" in answer["caveats"][0]


def test_a_file_with_syntax_errors_is_named_instead_of_silently_losing_its_definitions(
        tmp_path: Path, capsys):
    (tmp_path / "good.py").write_text("class Good:\n    pass\n")
    (tmp_path / "broken.py").write_text("class Broken(\n    def x(:\n")
    _, answer, _ = _ask(capsys, "find", "Broken", "--root", str(tmp_path), "--output", "json")
    assert answer["matches"] == []          # the definition did not survive the parse...
    (note,) = answer["caveats"]             # ...and the answer says so, naming the file
    assert "1 file(s) have syntax errors" in note and "broken.py" in note
    _, clean, _ = _ask(capsys, "find", "Good", "--root", str(tmp_path), "--output", "json")
    assert [m["name"] for m in clean["matches"]] == ["Good"]
    assert "good.py" not in " ".join(clean["caveats"])


def test_a_clean_project_has_no_caveats(sample_project: Path, capsys):
    _, answer, _ = _ask(capsys, "find", "Store", "--root", str(sample_project), "--output", "json")
    assert answer["caveats"] == []


# ---- Read-only commands honour `exclude` and ignore `[rules]` ----------------------

def test_primitives_apply_exclude_and_ignore_stale_rule_config(sample_project: Path, capsys):
    # One config carries both a rule slop no longer has and an exclude. The read-only
    # commands must take the exclude and not trip on the rule; `lint` must still reject it.
    (sample_project / "tests").mkdir()
    (sample_project / "tests" / "test_address.py").write_text("class Address:\n    pass\n")
    (sample_project / ".slop.toml").write_text(
        'exclude = ["tests/**"]\n[rules.complexity]\nenabled = true\n')
    code, answer, err = _ask(capsys, "find", "Address", "--root", str(sample_project), "--output", "json")
    assert code == 0, err
    assert [m["path"] for m in answer["matches"]] == ["store/address.py"]
    with pytest.raises(ValueError, match="unknown rule 'complexity'"):
        cli.lint(sample_project, "json")


def test_without_exclude_the_same_files_are_carved(sample_project: Path, capsys):
    (sample_project / "tests").mkdir()
    (sample_project / "tests" / "test_address.py").write_text("class Address:\n    pass\n")
    _, answer, _ = _ask(capsys, "find", "Address", "--root", str(sample_project), "--output", "json")
    assert sorted(m["path"] for m in answer["matches"]) == ["store/address.py", "tests/test_address.py"]


# ---- Q: what is the shape of a class? ---------------------------------------

def _shape_project(tmp_path: Path) -> Path:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "split.py").write_text(
        "class Split:\n"
        "    def f(self): return self.a\n"
        "    def g(self): return self.b\n"
        "    def h(self): return 1\n"
    )
    (tmp_path / "pkg" / "whole.py").write_text(
        "class Whole:\n    def f(self): return self.a\n    def g(self): return self.a\n")
    (tmp_path / "Thing.java").write_text("class Thing { int x; int f() { return x; } }")
    return tmp_path


def test_shape_reports_every_class_unfiltered(tmp_path: Path, capsys):
    root = _shape_project(tmp_path)
    code, answer, err = _ask(capsys, "shape", "--root", str(root), "--output", "json")
    assert code == 0, err
    rows = {r["name"]: r for r in answer["classes"]}
    # No floors: the cohesive class and the one-method class are answered too.
    assert set(rows) == {"Split", "Whole", "Thing"}
    assert (rows["Split"]["lcom4"], rows["Split"]["method_groups"], rows["Split"]["detached"]) == \
        (2, [["f"], ["g"]], ["h"])
    assert (rows["Whole"]["lcom4"], rows["Whole"]["method_groups"]) == (1, [["f", "g"]])
    assert rows["Split"]["path"] == "pkg/split.py" and rows["Split"]["line"] == 1
    assert {"nom", "dit", "noc", "cbo"} <= set(rows["Split"])


def test_shape_says_null_not_zero_where_cohesion_is_unmeasurable(tmp_path: Path, capsys):
    root = _shape_project(tmp_path)
    _, answer, _ = _ask(capsys, "shape", "--root", str(root), "--output", "json")
    thing = next(r for r in answer["classes"] if r["name"] == "Thing")
    assert (thing["lcom4"], thing["method_groups"], thing["detached"]) == (None, None, None)


def test_shape_scope_narrows_to_one_module(tmp_path: Path, capsys):
    root = _shape_project(tmp_path)
    code, answer, err = _ask(capsys, "shape", "--root", str(root), "--scope", "pkg/whole.py",
                             "--output", "json")
    assert code == 0, err
    assert [r["name"] for r in answer["classes"]] == ["Whole"]


def test_shape_human_output_lists_the_groups(tmp_path: Path, capsys):
    root = _shape_project(tmp_path)
    code, out, _ = _ask(capsys, "shape", "--root", str(root), "--scope", "pkg/split.py")
    assert code == 0
    assert "lcom4 2" in out and "groups: {f} {g}" in out and "detached: h" in out


def test_shape_scoped_to_a_class_returns_it_and_what_it_nests(tmp_path: Path, capsys):
    # The start scope itself is reported; a same-named class elsewhere is not.
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "split.py").write_text(
        "class Split:\n    def f(self): return self.a\n    class Inner:\n        def g(self): return self.b\n")
    (tmp_path / "pkg" / "other.py").write_text("class Split:\n    pass\n")
    code, answer, err = _ask(capsys, "shape", "--root", str(tmp_path), "--scope", "split.Split",
                             "--output", "json")
    assert code == 0, err
    assert answer["kind"] == "class"
    assert [(r["qualname"], r["path"]) for r in answer["classes"]] == [
        ("split.Split", "pkg/split.py"), ("split.Split.Inner", "pkg/split.py")]


def test_shape_explains_a_null_lcom4_in_the_row(tmp_path: Path, capsys):
    root = _shape_project(tmp_path)
    _, answer, _ = _ask(capsys, "shape", "--root", str(root), "--output", "json")
    thing = next(r for r in answer["classes"] if r["name"] == "Thing")
    assert any("cohesion not measured" in c and "lcom4 is null" in c for c in thing["caveats"])
    measured = next(r for r in answer["classes"] if r["name"] == "Whole")
    assert not any("cohesion not measured" in c for c in measured["caveats"])
