"""CLI entry point for slop."""

from __future__ import annotations

import argparse
import json
import sys

from slop import __version__
from slop.color import bold, dim, green, red, set_color
from slop.config import generate_default_config, load_config
from slop.engine import run_lint
from slop.output import DEFAULT_MAX_VIOLATIONS, format_human, format_json, format_quiet
from slop.preflight import MissingBinary, check_required_binaries


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="slop",
        description="slop \u2014 agentic code quality linter",
        epilog="""\
Commands:
  lint         Run all enabled rules (default)
  check        Run rules for a specific category or rule
  init         Generate a default .slop.toml config file
  rules        List all available rules with thresholds
  schema       Print JSON schema of the config
  doctor       Check that required system binaries are installed

Examples:
  slop lint
  slop lint --root ./src --output json
  slop check complexity
  slop check complexity.cyclomatic
  slop check class.inheritance
  slop init                 # default profile
  slop init lax            # legacy / gradual adoption
  slop init strict         # greenfield / quality-focused
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"slop {__version__}")

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    lint_parser = subparsers.add_parser(
        "lint", help="Run all enabled rules against the codebase"
    )
    _add_common_args(lint_parser)

    check_parser = subparsers.add_parser(
        "check", help="Run rules for a specific category or rule"
    )
    check_parser.add_argument(
        "target", type=str,
        help=(
            "Category (e.g. 'complexity'), subcategory "
            "(e.g. 'class.inheritance'), or rule (e.g. 'complexity.cyclomatic')"
        ),
    )
    _add_common_args(check_parser)

    init_parser = subparsers.add_parser(
        "init", help="Generate a .slop.toml config file",
        description="Generate a .slop.toml config file with a named profile.",
    )
    init_parser.add_argument(
        "profile", nargs="?", default="default",
        choices=["default", "lax", "strict"],
        help="Config profile: default (balanced), lax (legacy/gradual), strict (greenfield)",
    )
    skill_parser = subparsers.add_parser(
        "skill", help="Install the slop agent skill into a directory",
        description="Copy the bundled slop agent skill files into the target directory.",
    )
    skill_parser.add_argument(
        "directory", type=str,
        help="Target directory (created if it doesn't exist)",
    )

    hook_parser = subparsers.add_parser(
        "hook", help="Install or remove a git pre-commit hook that runs slop",
        description="Install a git pre-commit hook that runs slop lint before each commit.",
    )
    hook_parser.add_argument(
        "--disable", action="store_true",
        help="Remove the slop pre-commit hook",
    )

    subparsers.add_parser("rules", help="List all available rules with thresholds")
    subparsers.add_parser("schema", help="Print config schema as JSON")
    subparsers.add_parser(
        "doctor",
        help="Check that required system binaries (fd, git, rg) are installed",
    )

    return parser


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--root", type=str, default=None, help="Repository root (overrides config)"
    )
    parser.add_argument(
        "--config", type=str, default=None, dest="config_path",
        help="Path to config file (overrides auto-discovery)"
    )
    parser.add_argument(
        "--output", choices=["human", "json", "quiet"], default="human",
        help="Output format (default: human)",
    )
    parser.add_argument(
        "--max-violations", type=int, default=DEFAULT_MAX_VIOLATIONS, metavar="N",
        help=f"Max violations shown per rule (default: {DEFAULT_MAX_VIOLATIONS}, 0 = unlimited)",
    )
    parser.add_argument(
        "--no-color", action="store_true",
        help="Disable colored output",
    )


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    if getattr(args, "no_color", False):
        set_color(False)

    if args.command is None:
        args.command = "lint"
        args.root = None
        args.config_path = None
        args.output = "human"
        args.max_violations = DEFAULT_MAX_VIOLATIONS
        args.no_color = False

    dispatch = {
        "init": lambda a: cmd_init(getattr(a, "profile", "default")),
        "skill": lambda a: cmd_skill(a.directory),
        "hook": lambda a: cmd_hook(disable=getattr(a, "disable", False)),
        "rules": lambda _: cmd_rules(),
        "schema": lambda _: cmd_schema(),
        "lint": cmd_lint,
        "check": cmd_check,
        "doctor": lambda _: cmd_doctor(),
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 0
    return handler(args)


def _load_and_run(args: argparse.Namespace, **lint_kwargs) -> int:
    """Shared logic for lint and check: load config, run engine, format output."""
    try:
        config = load_config(
            config_path=getattr(args, "config_path", None),
            root=getattr(args, "root", None),
        )
    except Exception as e:
        print(f"slop: config error: {e}", file=sys.stderr)
        return 2

    missing = check_required_binaries(config)
    if missing:
        _print_missing_binaries(missing)
        return 2

    display_root = args.root or config.root
    if args.root:
        config.root = args.root

    result = run_lint(config, display_root=display_root, **lint_kwargs)

    max_v = getattr(args, "max_violations", DEFAULT_MAX_VIOLATIONS)
    if max_v == 0:
        max_v = 999999  # unlimited

    if args.output == "json":
        print(format_json(result))
    elif args.output == "quiet":
        print(format_quiet(result))
    else:
        print(format_human(result, max_violations=max_v))

    if result.result == "error":
        return 2
    if result.result == "fail":
        return 1
    return 0


def _print_missing_binaries(missing: list[MissingBinary]) -> None:
    """Render a preflight error block to stderr when required binaries are absent."""
    header = red(bold("slop: missing required system binaries"))
    print(header, file=sys.stderr)
    print("", file=sys.stderr)
    for m in missing:
        rules_str = ", ".join(m.rules)
        print(f"  {red(chr(0x2717))} {bold(m.name)} \u2014 needed by {rules_str}", file=sys.stderr)
        if m.install:
            print(f"      install: {m.install}", file=sys.stderr)
    print("", file=sys.stderr)
    hint = dim("Install the missing binaries and retry. Run 'slop doctor' to recheck.")
    print(hint, file=sys.stderr)


def cmd_lint(args: argparse.Namespace) -> int:
    return _load_and_run(args)


def cmd_check(args: argparse.Namespace) -> int:
    from slop.rules import CATEGORIES, RULE_REGISTRY, RULES_BY_NAME

    target = args.target

    # Validate the target before running
    if "." in target:
        exact = target in RULES_BY_NAME
        prefix = any(r.name.startswith(target + ".") for r in RULE_REGISTRY)
        if not exact and not prefix:
            available = ", ".join(sorted(CATEGORIES))
            print(
                f"slop: unknown rule or category '{target}'\n"
                f"Available categories: {available}\n"
                f"Run 'slop rules' for full list.",
                file=sys.stderr,
            )
            return 2
        return _load_and_run(args, filter_rule=target)
    else:
        if target not in {r.category for r in RULE_REGISTRY}:
            available = ", ".join(sorted(CATEGORIES))
            print(
                f"slop: unknown category '{target}'\n"
                f"Available: {available}\n"
                f"Run 'slop rules' for full list.",
                file=sys.stderr,
            )
            return 2
        return _load_and_run(args, filter_category=target)


_HOOK_MARKER = "# --- slop pre-commit hook ---"
_HOOK_CONTENT = f"""\
#!/bin/sh
{_HOOK_MARKER}
slop lint --output quiet
"""


def cmd_hook(disable: bool = False) -> int:
    import stat
    import subprocess
    from pathlib import Path

    # Find the git repo root
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        repo_root = Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("slop: not inside a git repository", file=sys.stderr)
        return 2

    hook_path = repo_root / ".git" / "hooks" / "pre-commit"

    if disable:
        if not hook_path.exists():
            print("slop: no pre-commit hook to remove")
            return 0
        content = hook_path.read_text()
        if _HOOK_MARKER not in content:
            print("slop: pre-commit hook exists but was not installed by slop — leaving it alone")
            return 1
        hook_path.unlink()
        print(f"Removed slop pre-commit hook from {hook_path}")
        return 0

    # Install
    if hook_path.exists():
        content = hook_path.read_text()
        if _HOOK_MARKER in content:
            print("slop: pre-commit hook already installed")
            return 0
        print(
            f"slop: {hook_path} already exists (not installed by slop)\n"
            f"Add this line manually to your existing hook:\n"
            f"  slop lint --output quiet",
            file=sys.stderr,
        )
        return 1

    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text(_HOOK_CONTENT)
    # Make executable (Unix); no-op effect on Windows but harmless
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    print(f"Installed slop pre-commit hook → {hook_path}")
    return 0


def cmd_skill(directory: str) -> int:
    import importlib.resources
    from pathlib import Path

    target = Path(directory)

    # Locate bundled skill files inside the package
    skill_pkg = importlib.resources.files("slop") / "_skill"

    # Copy the skill tree to the target directory
    target.mkdir(parents=True, exist_ok=True)

    def _copy_tree(src, dst: Path) -> int:
        """Recursively copy from importlib resource to filesystem."""
        count = 0
        for item in src.iterdir():
            dest = dst / item.name
            if item.is_file():
                dest.write_bytes(item.read_bytes())
                count += 1
            elif item.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
                count += _copy_tree(item, dest)
        return count

    try:
        count = _copy_tree(skill_pkg, target)
    except Exception as e:
        print(f"slop: failed to copy skill files: {e}", file=sys.stderr)
        return 2

    print(f"Installed slop skill ({count} files) → {target}")
    return 0


def cmd_init(profile: str = "default") -> int:
    from pathlib import Path

    target = Path.cwd() / ".slop.toml"
    if target.exists():
        print(f"slop: {target} already exists", file=sys.stderr)
        return 1
    target.write_text(generate_default_config(profile))
    print(f"Created {target} (profile: {profile})")
    return 0


def _format_binary_status(name: str, info: dict) -> tuple[str, bool]:
    """Format one binary's doctor line. Returns (line, is_present)."""
    if info.get("available", False):
        path = info.get("path", "")
        version = info.get("version") or ""
        actual_name = info.get("actual_name")
        alias = f" (as {actual_name})" if actual_name else ""
        version_str = f" ({version})" if version else ""
        return f"  {green(chr(0x2713))} {bold(name):20s} {path}{alias}{version_str}", True
    install = info.get("install", "")
    line = f"  {red(chr(0x2717))} {bold(name):20s} missing"
    if install:
        line += f" \u2014 install: {install}"
    return line, False


def cmd_doctor() -> int:
    """Print the status of each system binary slop may shell out to.

    Exits 2 if any of fd / git / rg are missing. Reports all three regardless
    of the current config so users can diagnose before touching config.
    """
    from slop._util.doctor import run_doctor

    report = run_doctor()
    tools = report.get("tools", {})

    print(bold(f"slop doctor \u2014 slop {__version__}"))
    print("")

    all_present = True
    for name in ("fd", "rg", "git"):
        info = tools.get(name)
        if info is None:
            continue
        line, present = _format_binary_status(name, info)
        print(line)
        if not present:
            all_present = False

    print("")
    if all_present:
        print(green(bold("All required binaries are installed.")))
        return 0
    print(red(bold("Missing dependencies. See above for install instructions.")))
    return 2


def cmd_rules() -> int:
    from slop.rules import RULE_REGISTRY

    for rule in RULE_REGISTRY:
        enabled = "on" if rule.default_enabled else "off"
        threshold = getattr(rule, "threshold_label", "") or ""
        print(f"  {rule.name:32s} [{enabled:3s}] {threshold:10s} {rule.description}")
    return 0


def cmd_schema() -> int:
    from slop.config import DEFAULT_RULE_CONFIGS

    schema = {
        "type": "object",
        "properties": {
            "root": {"type": "string", "default": "."},
            "languages": {"type": "array", "items": {"type": "string"}, "default": []},
            "exclude": {"type": "array", "items": {"type": "string"}, "default": []},
            "rules": {
                "type": "object",
                "properties": {
                    category: {
                        "type": "object",
                        "properties": {
                            k: {"default": v} for k, v in defaults.items()
                        },
                    }
                    for category, defaults in DEFAULT_RULE_CONFIGS.items()
                },
            },
        },
    }
    print(json.dumps(schema, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
