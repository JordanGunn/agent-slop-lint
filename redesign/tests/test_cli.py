"""CLI subcommands — rules / check / doctor / init (plus the existing lint)."""
from __future__ import annotations

from pathlib import Path

from slop import cli


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
    assert "lexical.stutter" in names and "orphans" in names


def test_check_unknown_target_errors(capsys):
    assert cli.check("nonsense.rule", ".", "human") == 2


def test_check_filters_to_family(tmp_path: Path, capsys):
    (tmp_path / "m.py").write_text(
        "def f(a, b):\n" + "".join(f"    if a == {i}: b += {i}\n" for i in range(15)) + "    return b\n"
    )
    rc = cli.check("complexity", tmp_path, "json")
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


def test_init_writes_template(tmp_path: Path, capsys):
    assert cli.init(tmp_path) == 0
    cfg = (tmp_path / ".slop.toml").read_text()
    assert "[rules." in cfg
    # second init refuses to overwrite
    assert cli.init(tmp_path) == 2
