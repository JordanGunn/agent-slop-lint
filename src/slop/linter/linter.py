"""``Linter`` — the v2.0 entry-point class.

Composes a ``Tree``, owns the rule loop, replaces
``engine.run_lint(config)`` once the cutover intent lands.

See ``docs/planning/linter.md`` for the locked design.
"""
from __future__ import annotations

from pathlib import Path

from slop import __version__
from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.types import RuleDefinition, RuleResult
from slop.tree.tree import Tree

from .dispatch import apply_waivers, overall_status, select_rules
from .result import Result

__all__ = ["Linter"]


def _execute_rule_v2(
    rule_def: RuleDefinition,
    tree: Tree,
    rc: Rule,
    config: Config,
) -> RuleResult:
    """Dispatch one rule to its runner.

    Picks the view by category prefix: ``Lexicon`` for ``lexical.*``,
    ``Structure`` for everything else (complexity, class, packages,
    types, difficulty, deps, redundancy, duplication, god_module,
    magic_literals, hotspots, orphans).
    """
    view = (
        tree.lexicon
        if rule_def.category.startswith("lexical.")
        else tree.structure
    )
    try:
        result = rule_def.run(view, rc, config)
    except Exception as e:
        return RuleResult(
            rule=rule_def.name,
            status="error",
            errors=[f"{type(e).__name__}: {e}"],
        )
    if result.errors and result.status == "pass":
        result.status = "error"
    return result


class Linter:
    """Entry-point class — composes Tree, owns the rule loop."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.tree = Tree(
            Path(config.root).expanduser().resolve(),
            excludes=tuple(config.exclude or ()),
        )

    def run(
        self,
        *,
        filter_category: str | None = None,
        filter_rule: str | None = None,
        display_root: str = "",
    ) -> Result:
        """Scan the corpus, run rules, return Result."""
        self.tree.scan()

        try:
            rules_to_run = select_rules(filter_rule, filter_category)
        except KeyError as e:
            key = e.args[0]
            label = "rule" if filter_rule else "category"
            return Result(
                version=__version__,
                root=str(self.tree.root),
                languages=list(self.tree.languages_detected),
                display_root=display_root or str(self.tree.root),
                rule_results={
                    key: RuleResult(
                        rule=key, status="error",
                        errors=[f"Unknown {label}: {key}"],
                    )
                },
                verdict="error",
            )

        rule_results: dict[str, RuleResult] = {}
        rules_checked = 0
        rules_skipped = 0
        total_violations = 0
        total_advisories = 0
        total_waived = 0

        for rule_def in rules_to_run:
            rc = self.config.rule_config(rule_def.category)
            if not rc.enabled or rc.severity == "off":
                rule_results[rule_def.name] = RuleResult(rule=rule_def.name, status="skip")
                rules_skipped += 1
                continue

            result = _execute_rule_v2(rule_def, self.tree, rc, self.config)
            result = apply_waivers(result, self.config.waivers, self.tree.root)
            rule_results[rule_def.name] = result
            rules_checked += 1

            for v in result.violations:
                if v.severity == "error":
                    total_violations += 1
                else:
                    total_advisories += 1
            total_waived += len(result.waived_violations)

        return Result(
            version=__version__,
            root=str(self.tree.root),
            languages=list(self.tree.languages_detected),
            display_root=display_root or str(self.tree.root),
            rule_results=rule_results,
            rules_checked=rules_checked,
            rules_skipped=rules_skipped,
            slop_count=total_violations,
            advisory_count=total_advisories,
            waived_count=total_waived,
            verdict=overall_status(rule_results, total_violations),
        )
