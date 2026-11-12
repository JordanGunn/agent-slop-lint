"""Occurrences of a word in declared names, and the rename plan that replaces it."""
from __future__ import annotations

from pathlib import Path

from slop.ontology.occurrence import Edit, Occurrence, occurrences, rename
from slop.scope import scan_corpus

_USERS = """\
class GetUser:
    def load(self, get_cache):
        return get_cache

def get_user(userGet, target):
    get_local = 1
    return get_user(userGet, get_local)

GET_USER = get_user
"""

_USE = """\
from users import get_user, GetUser

def run():
    GetUser()
    return get_user(1, 2)
"""


def _corpus(tmp_path: Path):
    (tmp_path / "users.py").write_text(_USERS, encoding="utf-8")
    (tmp_path / "use.py").write_text(_USE, encoding="utf-8")
    return scan_corpus(tmp_path, config=None)


def test_occurrences_find_classes_callables_and_parameters_in_both_files(tmp_path: Path):
    found = occurrences("get", _corpus(tmp_path))
    users, use = str(tmp_path / "users.py"), str(tmp_path / "use.py")
    assert [(o.identifier, o.role, o.path, o.line) for o in found] == [
        (("GetUser"), "class", users, 1),
        ("get_cache", "parameter", users, 2),
        ("get_user", "callable", users, 5),
        ("userGet", "parameter", users, 5),
    ]
    assert Occurrence("get_user", "callable", users, 5, "users") in found
    assert use not in {o.path for o in found}      # use.py declares only `run`


def test_occurrences_match_whole_words_only(tmp_path: Path):
    names = {o.identifier for o in occurrences("get", _corpus(tmp_path))}
    assert "target" not in names
    assert occurrences("tar", _corpus(tmp_path)) == ()


def test_rename_covers_declarations_references_and_importers_in_every_case_style(tmp_path: Path):
    plan = rename("get", "fetch", _corpus(tmp_path))
    users, use = str(tmp_path / "users.py"), str(tmp_path / "use.py")
    assert plan == tuple(sorted(plan, key=lambda e: (e.path, e.line, e.column)))
    assert len(set(plan)) == len(plan)
    assert Edit(users, 1, 7, "GetUser", "FetchUser") in plan
    assert Edit(users, 2, 20, "get_cache", "fetch_cache") in plan
    assert Edit(users, 3, 16, "get_cache", "fetch_cache") in plan          # reference to the parameter
    assert Edit(users, 5, 5, "get_user", "fetch_user") in plan
    assert Edit(users, 5, 14, "userGet", "userFetch") in plan
    assert Edit(users, 7, 12, "get_user", "fetch_user") in plan             # recursive call
    assert Edit(users, 9, 12, "get_user", "fetch_user") in plan
    assert Edit(use, 1, 19, "get_user", "fetch_user") in plan               # the import
    assert Edit(use, 1, 29, "GetUser", "FetchUser") in plan
    assert Edit(use, 4, 5, "GetUser", "FetchUser") in plan                  # uses
    assert Edit(use, 5, 12, "get_user", "fetch_user") in plan


def test_rename_keeps_upper_case_style(tmp_path: Path):
    (tmp_path / "m.py").write_text("class GET_USER:\n    pass\n\nx = GET_USER()\n", encoding="utf-8")
    plan = rename("get", "fetch", scan_corpus(tmp_path, config=None))
    assert [(e.line, e.before, e.after) for e in plan] == [(1, "GET_USER", "FETCH_USER"), (4, "GET_USER", "FETCH_USER")]


def test_an_undeclared_local_is_not_in_the_plan(tmp_path: Path):
    plan = rename("get", "fetch", _corpus(tmp_path))
    assert not [e for e in plan if e.before == "get_local"]
    assert not [e for e in plan if e.before == "target"]


def test_rename_writes_nothing(tmp_path: Path):
    corpus = _corpus(tmp_path)
    rename("get", "fetch", corpus)
    assert (tmp_path / "users.py").read_text(encoding="utf-8") == _USERS


def test_rename_reaches_importers_of_a_module_whose_name_has_the_word(tmp_path: Path):
    (tmp_path / "get_helpers.py").write_text("def f():\n    pass\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("import get_helpers\n\nget_helpers.f()\n", encoding="utf-8")
    corpus = scan_corpus(tmp_path, config=None)
    assert [o.role for o in occurrences("get", corpus)] == ["module"]
    plan = rename("get", "fetch", corpus)
    main = str(tmp_path / "main.py")
    assert Edit(main, 1, 8, "get_helpers", "fetch_helpers") in plan
    assert Edit(main, 3, 1, "get_helpers", "fetch_helpers") in plan
    assert {e.path for e in plan} == {main}        # the module's own file is not text to edit


def test_a_parameter_is_renamed_only_in_its_own_file(tmp_path: Path):
    # Another file cannot refer to a parameter: b.py's get_x only shares the spelling.
    (tmp_path / "a.py").write_text("def f(get_x):\n    return get_x\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("print(get_x)\n", encoding="utf-8")
    plan = rename("get", "fetch", scan_corpus(tmp_path, config=None))
    assert [(Path(e.path).name, e.line, e.after) for e in plan] == [("a.py", 1, "fetch_x"), ("a.py", 2, "fetch_x")]
