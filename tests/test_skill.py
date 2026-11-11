"""Skills follow the Agent Skills spec, are built from their single sources, and install cleanly."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from slop import cli
from slop.infer.bundle import prose
from slop.infer.contract import schemas
from slop.skill.catalog import SKILLS
from slop.skill.install import InstallError, install
from slop.skill.model import MAX_DESCRIPTION_LENGTH, Skill

INFER = SKILLS["slop-infer"]


def _frontmatter(manifest: str) -> dict[str, str]:
    match = re.match(r"---\n(.*?)\n---\n", manifest, re.S)
    assert match, "SKILL.md must start with YAML frontmatter"
    fields = {}
    for line in match.group(1).splitlines():
        key, value = line.split(": ", 1)
        if key == "description":
            # Quoted as a JSON string, which is always a valid YAML scalar whatever the text holds.
            assert value.startswith('"') and value.endswith('"'), value
            value = json.loads(value)
        fields[key] = value
    return fields


@pytest.mark.parametrize("skill", SKILLS.values(), ids=list(SKILLS))
def test_every_skill_meets_the_spec(skill: Skill):
    manifest = skill.tree()["SKILL.md"]
    fields = _frontmatter(manifest)
    assert fields == {"name": skill.name, "description": skill.description}
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", fields["name"]) and len(fields["name"]) <= 64
    assert 0 < len(fields["description"]) <= MAX_DESCRIPTION_LENGTH
    assert len(manifest.splitlines()) < 500                           # the spec's ceiling for SKILL.md


@pytest.mark.parametrize("skill", SKILLS.values(), ids=list(SKILLS))
def test_every_file_a_manifest_names_is_in_the_skill(skill: Skill):
    tree = skill.tree()
    named = set(re.findall(r"`((?:references|assets|scripts)/[\w./-]+\.\w+)`", tree["SKILL.md"]))
    assert named and named <= set(tree), named - set(tree)


def test_the_infer_skill_carries_exactly_what_the_cli_prints():
    tree = INFER.tree()
    assert tree["references/instructions.md"] == prose.instructions()
    for name in prose.references():
        assert tree[f"references/{name}.md"] == prose.reference(name)
    for document, schema in schemas().items():
        assert json.loads(tree[f"assets/schemas/{document}.json"]) == schema
    expected = ({"SKILL.md", "references/instructions.md"} | {f"references/{n}.md" for n in prose.references()}
                | {f"assets/schemas/{d}.json" for d in schemas()})
    assert set(tree) == expected


def test_the_infer_skill_follows_its_sources_when_they_change(tmp_path: Path, monkeypatch):
    (tmp_path / "references" / "rubrics").mkdir(parents=True)
    (tmp_path / "instructions.md").write_text("changed\n", encoding="utf-8")
    (tmp_path / "references" / "rubrics" / "class-cohesion.md").write_text("new rubric\n", encoding="utf-8")
    monkeypatch.setattr(prose, "ROOT", tmp_path)
    rebuilt = INFER.tree()                                                 # read when built, not copied
    assert rebuilt["references/instructions.md"] == "changed\n"
    assert rebuilt["references/rubrics/class-cohesion.md"] == "new rubric\n"


@pytest.mark.parametrize("name", ["Slop", "-slop", "slop-", "slop--infer", "a" * 65, ""])
def test_a_name_the_spec_forbids_is_refused(name: str):
    with pytest.raises(ValueError, match="skill name"):
        Skill(name=name, description="d", body="b", files={})


def test_a_description_must_be_present_and_within_the_limit():
    for description in ("", "x" * (MAX_DESCRIPTION_LENGTH + 1)):
        with pytest.raises(ValueError, match="description"):
            Skill(name="ok", description=description, body="b", files={})
    Skill(name="ok", description="x" * MAX_DESCRIPTION_LENGTH, body="b", files={})


@pytest.mark.parametrize("path", ["../escape.md", "/abs.md", "references/../../x.md", "SKILL.md"])
def test_a_file_must_stay_inside_the_skill_and_not_shadow_the_manifest(path: str):
    with pytest.raises(ValueError, match="must stay inside"):
        Skill(name="ok", description="d", body="b", files={path: lambda: ""})


def test_a_description_with_quotes_and_colons_survives_the_frontmatter():
    skill = Skill(name="ok", description='Use when: "quoted" and `ticked`', body="b", files={})
    assert _frontmatter(skill.manifest())["description"] == 'Use when: "quoted" and `ticked`'


def test_install_writes_the_whole_tree_under_the_skill_name(tmp_path: Path):
    target = install(INFER, tmp_path)
    assert target == tmp_path / "slop-infer"
    written = {p.relative_to(target).as_posix(): p.read_text(encoding="utf-8") for p in target.rglob("*") if p.is_file()}
    assert written == INFER.tree()


def test_install_refuses_to_overwrite_unless_asked_and_then_replaces_cleanly(tmp_path: Path):
    target = install(INFER, tmp_path)
    (target / "stale.md").write_text("from an older install", encoding="utf-8")
    with pytest.raises(InstallError, match="use --force"):
        install(INFER, tmp_path)
    assert (target / "stale.md").exists()                                  # refused: nothing touched
    install(INFER, tmp_path, replace=True)
    assert not (target / "stale.md").exists() and (target / "SKILL.md").is_file()


def test_install_never_replaces_something_that_is_not_a_directory(tmp_path: Path):
    (tmp_path / "slop-infer").write_text("a file", encoding="utf-8")
    with pytest.raises(InstallError, match="not a skill directory"):
        install(INFER, tmp_path, replace=True)
    assert (tmp_path / "slop-infer").read_text(encoding="utf-8") == "a file"


def _run(capsys, *argv: str) -> tuple[int, str, str]:
    capsys.readouterr()
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_the_cli_lists_shows_and_installs(tmp_path: Path, capsys):
    code, out, _ = _run(capsys, "skill", "list")
    assert code == 0 and out.startswith("slop-infer  ")
    code, out, _ = _run(capsys, "skill", "show", "slop-infer")
    assert code == 0 and out == INFER.tree()["SKILL.md"]
    code, out, _ = _run(capsys, "skill", "show", "slop-infer", "assets/schemas/verdicts.json")
    assert code == 0 and json.loads(out) == schemas()["verdicts"]
    code, out, _ = _run(capsys, "skill", "install", "slop-infer", "--dest", str(tmp_path))
    assert code == 0 and out.strip() == str(tmp_path / "slop-infer")
    code, _, err = _run(capsys, "skill", "install", "slop-infer", "--dest", str(tmp_path))
    assert code == 2 and "use --force" in err
    code, _, _ = _run(capsys, "skill", "install", "slop-infer", "--dest", str(tmp_path), "--force")
    assert code == 0


def test_the_cli_names_what_it_cannot_find(capsys):
    code, _, err = _run(capsys, "skill", "show", "nope")
    assert code == 2 and "no skill 'nope'" in err
    code, _, err = _run(capsys, "skill", "show", "slop-infer", "nope.md")
    assert code == 2 and "has no file 'nope.md'" in err and "SKILL.md" in err
