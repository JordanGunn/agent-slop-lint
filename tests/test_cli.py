"""Tests for slop CLI entry points — preflight, doctor, and exit codes."""

from __future__ import annotations

import contextlib
import io
from pathlib import Path

from slop.cli import main


def _run(argv: list[str]) -> tuple[int, str, str]:
    """Invoke slop's CLI and capture stdout, stderr, and exit code."""
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


# ---------------------------------------------------------------------------
# Preflight: fail-fast when a required binary is missing
# ---------------------------------------------------------------------------


def test_lint_fails_fast_when_fd_missing(tmp_path: Path, monkeypatch):
    """Missing fd must exit 2 and print install instructions to stderr —
    not render silently as ✓ clean (the regression we're fixing)."""
    from slop import preflight

    def fake_check(name: str) -> dict:
        if name == "fd":
            return {
                "name": "fd",
                "available": False,
                "install": "https://github.com/sharkdp/fd#installation",
            }
        return {"name": name, "available": True, "path": "/usr/bin/" + name, "version": "1.0"}

    monkeypatch.setattr(preflight, "check_tool", fake_check)

    code, stdout, stderr = _run(["lint", "--root", str(tmp_path), "--no-color"])

    assert code == 2
    assert "missing required system binaries" in stderr
    assert "fd" in stderr
    assert "https://github.com/sharkdp/fd" in stderr
    # No rule output — preflight short-circuits before run_lint.
    assert "complexity" not in stdout.lower()


def test_lint_skips_binary_check_for_disabled_rules(tmp_path: Path, monkeypatch):
    """If hotspots is disabled, missing git should not block lint."""
    from slop import preflight

    (tmp_path / ".slop.toml").write_text(
        "[rules.hotspots]\nenabled = false\n"
        "[rules.orphans]\nenabled = false\n"
    )
    (tmp_path / "a.py").write_text("x = 1\n")

    seen: list[str] = []

    def fake_check(name: str) -> dict:
        seen.append(name)
        if name == "git":
            return {"name": "git", "available": False, "install": "x"}
        return {"name": name, "available": True, "path": "/" + name, "version": "1"}

    monkeypatch.setattr(preflight, "check_tool", fake_check)

    code, _stdout, stderr = _run(["lint", "--root", str(tmp_path), "--no-color"])

    assert code == 0, f"expected 0, got {code}. stderr:\n{stderr}"
    assert "git" not in seen  # hotspots disabled → git was never queried


def test_lint_with_all_deps_present_runs_normally(tmp_path: Path, monkeypatch):
    from slop import preflight

    # Disable hotspots so the test doesn't require a git repo in tmp_path.
    (tmp_path / ".slop.toml").write_text("[rules.hotspots]\nenabled = false\n")
    (tmp_path / "a.py").write_text("x = 1\n")

    monkeypatch.setattr(
        preflight, "check_tool",
        lambda name: {"name": name, "available": True, "path": "/" + name, "version": "1"},
    )

    code, stdout, _stderr = _run(["lint", "--root", str(tmp_path), "--no-color"])

    assert code in (0, 1)  # 0 if no violations, 1 if some — either way not a preflight error
    assert "missing required system binaries" not in stdout


# ---------------------------------------------------------------------------
# Doctor subcommand
# ---------------------------------------------------------------------------


def test_doctor_reports_all_present(monkeypatch):
    def fake_run_doctor() -> dict:
        return {
            "ok": True,
            "tools": {
                "fd": {"name": "fd", "available": True, "path": "/usr/bin/fd", "version": "10.2.0"},
                "rg": {"name": "rg", "available": True, "path": "/usr/bin/rg", "version": "14.0.0"},
                "git": {"name": "git", "available": True, "path": "/usr/bin/git", "version": "2.43.0"},
            },
            "python_packages": {},
            "message": "All dependencies available",
        }

    # cmd_doctor imports run_doctor lazily inside the function.
    import aux.util.doctor as doctor_mod
    monkeypatch.setattr(doctor_mod, "run_doctor", fake_run_doctor)

    code, stdout, _stderr = _run(["doctor"])
    assert code == 0
    assert "fd" in stdout
    assert "rg" in stdout
    assert "git" in stdout
    assert "/usr/bin/fd" in stdout


def test_doctor_exits_2_when_binary_missing(monkeypatch):
    def fake_run_doctor() -> dict:
        return {
            "ok": False,
            "tools": {
                "fd": {
                    "name": "fd",
                    "available": False,
                    "install": "https://github.com/sharkdp/fd#installation",
                },
                "rg": {"name": "rg", "available": True, "path": "/usr/bin/rg", "version": "14"},
                "git": {"name": "git", "available": True, "path": "/usr/bin/git", "version": "2.43"},
            },
            "python_packages": {},
            "message": "Some dependencies missing",
        }

    import aux.util.doctor as doctor_mod
    monkeypatch.setattr(doctor_mod, "run_doctor", fake_run_doctor)

    code, stdout, _stderr = _run(["doctor"])
    assert code == 2
    assert "missing" in stdout.lower()
    assert "https://github.com/sharkdp/fd" in stdout
