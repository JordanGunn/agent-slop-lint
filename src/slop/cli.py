"""CLI entry point for slop."""

from __future__ import annotations

import argparse
import json
import sys

from slop import __version__
from slop.color import set_color
from slop.config import generate_default_config, load_config
from slop.engine import run_lint
from slop.output import DEFAULT_MAX_VIOLATIONS, format_human, format_json, format_quiet


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
    subparsers.add_parser("rules", help="List all available rules with thresholds")
    subparsers.add_parser("schema", help="Print config schema as JSON")

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

    # Handle color before any output
    if getattr(args, "no_color", False):
        set_color(False)

    if args.command is None:
        args.command = "lint"
        args.root = None
        args.config_path = None
        args.output = "human"
        args.max_violations = DEFAULT_MAX_VIOLATIONS
        args.no_color = False

    if args.command == "init":
        return cmd_init(getattr(args, "profile", "default"))
    if args.command == "rules":
        return cmd_rules()
    if args.command == "schema":
        return cmd_schema()
    if args.command == "lint":
        return cmd_lint(args)
    if args.command == "check":
        return cmd_check(args)

    parser.print_help()
    return 0


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


def cmd_init(profile: str = "default") -> int:
    from pathlib import Path

    target = Path.cwd() / ".slop.toml"
    if target.exists():
        print(f"slop: {target} already exists", file=sys.stderr)
        return 1
    target.write_text(generate_default_config(profile))
    print(f"Created {target} (profile: {profile})")
    return 0


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
