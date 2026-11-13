"""Skills follow the Agent Skills spec, are built from their single sources, and install cleanly."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from slop import cli
from slop.skill.catalog import SKILLS
from slop.skill.install import RECORD, InstallError, install
from slop.skill.model import MAX_DESCRIPTION_LENGTH, Skill

SLOP = SKILLS["slop"]


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
    assert named <= set(tree), named - set(tree)


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


def _files(target: Path) -> dict[str, str]:
    return {p.relative_to(target).as_posix(): p.read_text(encoding="utf-8") for p in target.rglob("*") if p.is_file()}


def _skill(files: dict) -> Skill:
    return Skill(name="slop", description="d", body="b", files=files)


def test_install_writes_the_whole_tree_and_records_what_it_wrote(tmp_path: Path):
    target = install(SLOP, tmp_path)
    assert target == tmp_path / "slop"
    written = _files(target)
    record = json.loads(written.pop(RECORD))
    assert written == SLOP.tree()
    assert record["skill"] == "slop" and record["files"] == sorted(SLOP.tree()) and record["slop"]


def test_install_refuses_an_existing_install_unless_asked(tmp_path: Path):
    target = install(SLOP, tmp_path)
    before = _files(target)
    with pytest.raises(InstallError, match="use --force"):
        install(SLOP, tmp_path)
    assert _files(target) == before


def test_replacing_keeps_what_the_user_added_and_drops_what_the_skill_no_longer_has(tmp_path: Path):
    target = install(_skill({"references/old.md": lambda: "old", "references/keep.md": lambda: "v1"}), tmp_path)
    (target / "references" / "notes.md").write_text("mine", encoding="utf-8")
    install(_skill({"references/keep.md": lambda: "v2", "assets/new.json": lambda: "{}"}), tmp_path, replace=True)
    files = _files(target)
    assert files["references/keep.md"] == "v2" and files["assets/new.json"] == "{}"
    assert "references/old.md" not in files                               # it wrote it before; it is gone now
    assert files["references/notes.md"] == "mine"                          # the user's file stays


def test_a_directory_left_empty_by_the_replacement_is_removed(tmp_path: Path):
    target = install(_skill({"references/notes/a.md": lambda: "a"}), tmp_path)
    install(_skill({"assets/b.json": lambda: "{}"}), tmp_path, replace=True)
    assert not (target / "references").exists()


def test_a_directory_slop_did_not_install_is_never_replaced(tmp_path: Path):
    target = tmp_path / "slop"
    target.mkdir()
    (target / "SKILL.md").write_text("someone else's", encoding="utf-8")
    with pytest.raises(InstallError, match="was not installed by slop"):
        install(SLOP, tmp_path, replace=True)
    assert _files(target) == {"SKILL.md": "someone else's"}


def test_an_install_of_another_skill_or_a_damaged_record_is_never_replaced(tmp_path: Path):
    target = install(SLOP, tmp_path)
    for record in ('{"skill": "other", "files": []}', "{not json", '{"skill": "slop", "files": ["../../outside"]}'):
        (target / RECORD).write_text(record, encoding="utf-8")
        with pytest.raises(InstallError, match="was not installed by slop"):
            install(SLOP, tmp_path, replace=True)
    (tmp_path / "outside").write_text("must survive", encoding="utf-8")
    assert (tmp_path / "outside").read_text(encoding="utf-8") == "must survive"


def test_a_skill_that_fails_to_build_leaves_the_installed_one_untouched(tmp_path: Path):
    target = install(SLOP, tmp_path)
    before = _files(target)

    def broken() -> str:
        raise OSError("source unreadable")

    with pytest.raises(OSError):
        install(_skill({"references/x.md": broken}), tmp_path, replace=True)
    assert _files(target) == before


def test_install_never_replaces_something_that_is_not_a_directory(tmp_path: Path):
    (tmp_path / "slop").write_text("a file", encoding="utf-8")
    with pytest.raises(InstallError, match="not a skill directory"):
        install(SLOP, tmp_path, replace=True)
    assert (tmp_path / "slop").read_text(encoding="utf-8") == "a file"


def _run(capsys, *argv: str) -> tuple[int, str, str]:
    capsys.readouterr()
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_the_cli_lists_shows_and_installs(tmp_path: Path, capsys):
    code, out, _ = _run(capsys, "skill", "list")
    assert code == 0 and out.startswith("slop  ")
    code, out, _ = _run(capsys, "skill", "show", "slop")
    assert code == 0 and out == SLOP.tree()["SKILL.md"]
    code, out, _ = _run(capsys, "skill", "install", "slop", "--dest", str(tmp_path))
    assert code == 0 and out.strip() == str(tmp_path / "slop")
    code, _, err = _run(capsys, "skill", "install", "slop", "--dest", str(tmp_path))
    assert code == 2 and "use --force" in err
    code, _, _ = _run(capsys, "skill", "install", "slop", "--dest", str(tmp_path), "--force")
    assert code == 0


def test_the_cli_names_what_it_cannot_find(capsys):
    code, _, err = _run(capsys, "skill", "show", "nope")
    assert code == 2 and "no skill 'nope'" in err
    code, _, err = _run(capsys, "skill", "show", "slop", "nope.md")
    assert code == 2 and "has no file 'nope.md'" in err and "SKILL.md" in err


def test_the_slop_skill_names_every_top_level_command_and_no_other():
    from slop import cli
    import argparse
    parser = cli.parser()
    [commands] = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
    table = SLOP.body.split("## Capabilities", 1)[1].split("\n## ", 1)[0]
    named = set(re.findall(r"`slop (\w+)", table))
    assert named == set(commands.choices), (set(commands.choices) - named, named - set(commands.choices))


def test_the_slop_skill_points_the_agent_at_the_live_help_menu():
    assert "`slop --help`" in SLOP.body and "`slop COMMAND --help`" in SLOP.body
