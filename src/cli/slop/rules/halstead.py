"""Information rules — wraps slop._structural halstead_kernel.

Rules:
  information.volume      — fail if any function's Volume exceeds threshold
  information.difficulty  — fail if any function's Difficulty exceeds threshold

Halstead (1977) derived metrics from operator/operand counts:
  Volume     = Length * log2(Vocabulary)   — information content
  Difficulty = (n1/2) * (N2/n2)            — reader cognitive burden

Optional refinement for ``information.volume``:

  token_weight_alpha (float, default 0.0)
    When > 0, the measured Volume is scaled up for functions whose identifiers
    average fewer than 2 word-tokens each.  The formula is:

      penalty  = 1 + alpha * max(0, 2.0 - mean_tokens_per_identifier)
      adjusted = Volume * penalty

    This tightens the effective threshold for terse-identifier code without
    changing the threshold for well-named functions.  It is opt-in (alpha=0)
    so existing configurations are unaffected.
"""

from __future__ import annotations

from pathlib import Path

from slop._structural.halstead import HalsteadResult, halstead_kernel
from slop.models import RuleConfig, RuleResult, SlopConfig, Violation

#: Reference mean tokens expected for "well-named" code.
_MEAN_TOKEN_REFERENCE = 2.0


def _run_halstead(root: Path, config: SlopConfig) -> HalsteadResult:
    return halstead_kernel(
        root=root,
        languages=config.languages or None,
        excludes=config.exclude or None,
    )


def _token_penalty_map(
    root: Path,
    slop_config: SlopConfig,
) -> dict[tuple[str, int], float]:
    """Build a (rel_file, line) → penalty multiplier map via the lexical kernel.

    Returns an empty dict when the lexical kernel is unavailable (e.g. no
    tree-sitter grammars installed for the active languages).
    """
    try:
        from slop._lexical.identifier_tokens import identifier_token_kernel
        lr = identifier_token_kernel(
            root=root,
            languages=slop_config.languages or None,
            excludes=slop_config.exclude or None,
        )
        # Index by (relative file path, start line) — same key as HalsteadMetrics
        return {
            (fn.file, fn.line): fn.mean_tokens
            for fn in lr.functions
        }
    except Exception:
        return {}


def run_volume(root: Path, rule_config: RuleConfig, slop_config: SlopConfig) -> RuleResult:
    """Check Halstead Volume per function against threshold.

    When ``token_weight_alpha > 0``, a naming-terse penalty is applied to the
    measured Volume before comparing against the threshold.
    """
    threshold: float = rule_config.params.get("threshold", 1000)
    alpha: float = rule_config.params.get("token_weight_alpha", 0.0)
    severity = rule_config.severity

    result = _run_halstead(root, slop_config)

    mean_tokens_map: dict[tuple[str, int], float] = (
        _token_penalty_map(root, slop_config) if alpha > 0 else {}
    )

    violations: list[Violation] = []
    for fn in result.functions:
        volume = fn.volume
        penalty = 1.0
        if alpha > 0:
            mean_tokens = mean_tokens_map.get((fn.file, fn.line), _MEAN_TOKEN_REFERENCE)
            terse_factor = max(0.0, _MEAN_TOKEN_REFERENCE - mean_tokens)
            penalty = 1.0 + alpha * terse_factor
            volume = volume * penalty

        if volume > threshold:
            violations.append(
                Violation(
                    rule="information.volume",
                    file=fn.file,
                    line=fn.line,
                    symbol=fn.name,
                    message=(
                        f"Volume {fn.volume:.0f}"
                        + (f" (adjusted {volume:.0f})" if penalty != 1.0 else "")
                        + f" exceeds {threshold}"
                    ),
                    severity=severity,
                    value=round(volume, 2),
                    threshold=threshold,
                    metadata={
                        "raw_volume": fn.volume,
                        "penalty": round(penalty, 3),
                        "difficulty": fn.difficulty,
                        "effort": fn.effort,
                        "vocabulary": fn.vocabulary,
                        "length": fn.length,
                        "end_line": fn.end_line,
                    },
                )
            )

    return RuleResult(
        rule="information.volume",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": result.functions_analyzed,
            "violation_count": len(violations),
            "token_weight_alpha": alpha,
        },
        errors=list(result.errors),
    )


def run_difficulty(root: Path, rule_config: RuleConfig, slop_config: SlopConfig) -> RuleResult:
    """Check Halstead Difficulty per function against threshold."""
    threshold = rule_config.params.get("threshold", 30)
    severity = rule_config.severity

    result = _run_halstead(root, slop_config)

    violations: list[Violation] = []
    for fn in result.functions:
        if fn.difficulty > threshold:
            violations.append(
                Violation(
                    rule="information.difficulty",
                    file=fn.file,
                    line=fn.line,
                    symbol=fn.name,
                    message=f"Difficulty {fn.difficulty:.1f} exceeds {threshold}",
                    severity=severity,
                    value=fn.difficulty,
                    threshold=threshold,
                    metadata={
                        "volume": fn.volume,
                        "effort": fn.effort,
                        "vocabulary": fn.vocabulary,
                        "length": fn.length,
                        "end_line": fn.end_line,
                    },
                )
            )

    return RuleResult(
        rule="information.difficulty",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "functions_checked": result.functions_analyzed,
            "violation_count": len(violations),
        },
        errors=list(result.errors),
    )
