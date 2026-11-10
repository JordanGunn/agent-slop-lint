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


@pytest.mark.parametrize("filename,source", [
    ("m.c", "struct Widget { int x; };\n"),
    ("m.jl", "struct Widget\nend\n"),
])
def test_a_grammar_without_class_scopes_says_so_instead_of_answering_empty(
        tmp_path: Path, capsys, filename: str, source: str):
    # An empty 'matches' here would read as "Widget is not defined". It is defined; the
    # grammar just carves no class scopes, so the answer must carry that caveat.
    (tmp_path / filename).write_text(source)
    _, answer, _ = _ask(capsys, "find", "Widget", "--root", str(tmp_path), "--output", "json")
    assert answer["matches"] == []
    assert len(answer["caveats"]) == 1 and "no class scopes" in answer["caveats"][0]
    code, text, _ = _ask(capsys, "find", "Widget", "--root", str(tmp_path))
    assert "note:" in text


def test_caveats_apply_only_to_questions_about_classes(tmp_path: Path, capsys):
    (tmp_path / "m.c").write_text("int run(void) { return 1; }\n")
    _, answer, _ = _ask(capsys, "find", "run", "--kind", "callable", "--root", str(tmp_path),
                        "--output", "json")
    assert [m["name"] for m in answer["matches"]] == ["run"]
    assert answer["caveats"] == []       # callables are discoverable in C


def test_vocab_carries_the_caveat_for_a_polyglot_root(tmp_path: Path, capsys):
    (tmp_path / "a.py").write_text("class Ticket:\n    pass\n")
    (tmp_path / "b.c").write_text("struct Customer { int x; };\n")
    _, answer, _ = _ask(capsys, "vocab", "--ontology", IR, "--root", str(tmp_path), "--output", "json")
    assert [m["term"] for m in answer["matched"]] == ["Ticket"]
    assert any(c.startswith("c:") for c in answer["caveats"])   # Customer may live in C
