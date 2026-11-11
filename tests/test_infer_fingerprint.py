"""Finding identity survives moves; the fingerprint changes when what a verdict rests on does."""
from __future__ import annotations

from slop.infer.frame.fingerprint import code_fingerprint
from slop.violation import finding_id


def test_a_finding_id_is_stable_and_depends_on_rule_path_and_subject():
    base = finding_id("class-cohesion", "a.py", "a.A")
    assert base == finding_id("class-cohesion", "a.py", "a.A")
    assert len({base, finding_id("rigid-package", "a.py", "a.A"), finding_id("class-cohesion", "b.py", "a.A"),
                finding_id("class-cohesion", "a.py", "a.B")}) == 4


def test_a_key_tells_apart_findings_about_one_subject_and_no_key_keeps_the_old_id():
    base = finding_id("duplicate-string", "a.py", "a")
    assert len({base, finding_id("duplicate-string", "a.py", "a", '"x"'), finding_id("duplicate-string", "a.py", "a", '"y"')}) == 3
    assert finding_id("class-cohesion", "a.py", "a.A") == "570232cdd89ce029"   # the id every stored ruling keys on


def test_the_fields_of_an_id_cannot_run_together():
    assert finding_id("ab", "c", "d") != finding_id("a", "bc", "d")


def test_the_fingerprint_follows_the_code_and_the_rubric_version():
    base = code_fingerprint("class A:\n    pass\n", "v1")
    assert base == code_fingerprint("class A:\n    pass\n", "v1")
    assert base != code_fingerprint("class A:\n    pass  \n", "v1")      # the code changed
    assert base != code_fingerprint("class A:\n    pass\n", "v2")        # the rubric changed


def test_line_endings_do_not_change_the_fingerprint():
    assert code_fingerprint("a\r\nb\r\n", "v1") == code_fingerprint("a\nb\n", "v1")
