"""lexical.hammers — flag catchall identifier vocabulary against a banlist.

When all you have is a hammer, everything looks like a nail.
``Manager``, ``Helper``, ``Util``, ``Spec``, ``Object`` are the
nouns the codebase reaches for when it doesn't have a real one —
hammering every responsibility into the same shape.

Configurable: pass ``terms`` (list of {word, positions, severity,
exempt_when}) to override the default profile.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from slop.linter.rule import Rule
from slop.config import Config
from slop.linter.slop import Slop
from slop.linter.types import RuleResult
from slop.linter.tags import Tag
from slop.linter.types import RuleDefinition

if TYPE_CHECKING:
    from slop.lexicon.view import Lexicon


@dataclass(frozen=True)
class HammerTerm:
    word: str
    positions: tuple[str, ...]
    severity: str | None = None
    exempt_when: tuple[str, ...] = ()


DEFAULT_PROFILE: tuple[HammerTerm, ...] = (
    HammerTerm("Manager",       ("suffix",), "warning"),
    HammerTerm("Coordinator",   ("suffix",), "warning"),
    HammerTerm("Helper",        ("any", "module_name"), "warning"),
    HammerTerm("Utility",       ("any", "module_name"), "warning"),
    HammerTerm("Util",          ("any", "module_name"), "warning"),
    HammerTerm("Utils",         ("any", "module_name"), "warning"),
    HammerTerm("Handler",       ("suffix",), "info"),
    HammerTerm("Processor",     ("suffix",), "info"),
    HammerTerm("Service",       ("suffix",), "info"),
    HammerTerm("Provider",      ("suffix",), "info"),
    HammerTerm("Engine",        ("suffix",), "info"),
    HammerTerm("Factory",       ("suffix",), "info"),
    HammerTerm("Builder",       ("suffix",), "info"),
    HammerTerm("Wrapper",       ("suffix",), "info"),
    HammerTerm("Adapter",       ("suffix",), "info"),
    HammerTerm("Spec",          ("suffix",), "warning",
               exempt_when=("module_is_test",)),
    HammerTerm("Specification", ("suffix",), "warning",
               exempt_when=("module_is_test",)),
    HammerTerm("Base",          ("suffix",), "warning"),
    HammerTerm("Abstract",      ("prefix",), "info"),
    HammerTerm("Object",        ("suffix",), "error"),
    HammerTerm("Item",          ("suffix",), "error"),
    HammerTerm("Element",       ("suffix",), "error"),
    HammerTerm("Thing",         ("suffix",), "error"),
    HammerTerm("Data",          ("suffix",), "warning"),
    HammerTerm("Info",          ("suffix",), "warning"),
    HammerTerm("Container",     ("suffix",), "warning"),
    HammerTerm("Holder",        ("suffix",), "warning"),
    HammerTerm("Common",        ("module_name", "suffix"), "warning"),
    HammerTerm("Core",          ("module_name", "suffix"), "warning"),
    HammerTerm("Misc",          ("module_name", "suffix"), "warning"),
    HammerTerm("Extra",         ("module_name", "suffix"), "warning"),
    HammerTerm("Shared",        ("module_name", "suffix"), "warning"),
    HammerTerm("Stuff",         ("any",), "error"),
    HammerTerm("Things",        ("any",), "error"),
)


_TEST_PATH_RE = re.compile(r"(^|/)tests?/|test_|_test\.|\.test\.")
_MAIN_PATH_RE = re.compile(r"(^|/)(__main__|main)\.[a-z]+$")


def _terms_from_config(rule_config: Rule) -> tuple[HammerTerm, ...]:
    raw = rule_config.params.get("terms")
    if not raw:
        return DEFAULT_PROFILE
    parsed: list[HammerTerm] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        word = entry.get("word")
        positions = entry.get("positions") or ["suffix"]
        if not word:
            continue
        parsed.append(HammerTerm(
            word=str(word),
            positions=tuple(str(p) for p in positions),
            severity=entry.get("severity"),
            exempt_when=tuple(str(e) for e in (entry.get("exempt_when") or ())),
        ))
    return tuple(parsed) if parsed else DEFAULT_PROFILE


def _is_exempt(term: HammerTerm, file_path: str) -> bool:
    for predicate in term.exempt_when:
        if predicate == "module_is_test" and _TEST_PATH_RE.search(file_path):
            return True
        if predicate == "module_is_main" and _MAIN_PATH_RE.search(file_path):
            return True
    return False


def _check_identifier(
    tokens: tuple[str, ...],
    by_word: dict[str, HammerTerm],
    file_path: str,
    default_severity: str,
) -> tuple[str, str, str] | None:
    """If any token matches a configured term in its positions, return
    ``(matched_word, matched_position, severity)``."""
    if not tokens:
        return None
    first_lower = tokens[0].lower()
    last_lower = tokens[-1].lower()
    for token in tokens:
        term = by_word.get(token.lower())
        if term is None:
            continue
        if _is_exempt(term, file_path):
            continue
        positions = set(term.positions)
        token_lower = token.lower()
        if "prefix" in positions and token_lower == first_lower:
            return (term.word, "prefix", term.severity or default_severity)
        if "suffix" in positions and token_lower == last_lower:
            return (term.word, "suffix", term.severity or default_severity)
        if "any" in positions:
            return (term.word, "any", term.severity or default_severity)
    return None


def _check_module_name(
    stem: str,
    by_word: dict[str, HammerTerm],
    file_path: str,
    default_severity: str,
) -> tuple[str, str] | None:
    """Check the file stem against terms with ``module_name`` position."""
    from slop.lexicon.view import Lexicon as _Lex
    tokens = _Lex.split_tokens(stem)
    if not tokens:
        return None
    for token in tokens:
        term = by_word.get(token.lower())
        if term is None:
            continue
        if "module_name" not in term.positions:
            continue
        if _is_exempt(term, file_path):
            continue
        return (term.word, term.severity or default_severity)
    return None


def run_hammers(
    lexicon: Lexicon, rule_config: Rule, slop_config: Config,
) -> RuleResult:
    """Flag callable / class / module names that match the catchall banlist."""
    terms = _terms_from_config(rule_config)
    default_severity = rule_config.severity
    by_word: dict[str, HammerTerm] = {t.word.lower(): t for t in terms}
    root = Path(slop_config.root).expanduser().resolve() if slop_config.root else None

    # Distribution signals for hammer-pervasiveness context. A banlist
    # match is more urgent when the hammer token is high-spread and
    # isolate (appears everywhere but bonds with no specific partner —
    # the hammer has been institutionalized).
    from slop.lexicon.affix import UNIVERSAL_NOISE
    spread_map = {
        t: len(files)
        for t, files in lexicon.token_locations(exclude=UNIVERSAL_NOISE).items()
    }
    isolate_tokens = frozenset(
        t for t, _ in lexicon.packet_isolates(
            min_bags=3, min_association=0.7,
            min_frequency=3, exclude=UNIVERSAL_NOISE,
        )
    )

    def _relfile(p: str) -> str:
        if root is None:
            return p
        try:
            return str(Path(p).relative_to(root))
        except ValueError:
            return p

    def _pervasiveness_note(word: str) -> str:
        token = word.lower()
        spread = spread_map.get(token, 0)
        is_isolate = token in isolate_tokens
        if spread >= 5 and is_isolate:
            return (
                f" The token appears in {spread} files and bonds with "
                f"no specific partner — the hammer has been "
                f"institutionalized across the codebase."
            )
        if spread >= 5:
            return f" The token appears in {spread} files."
        return ""

    violations: list[Slop] = []
    items_analyzed = 0

    # 1 + 2. Function and class names.
    for entity in lexicon.named_entities():
        items_analyzed += 1
        rel = _relfile(entity.file)
        hit = _check_identifier(entity.tokens, by_word, rel, default_severity)
        if hit is None:
            continue
        word, pos, severity = hit
        token_lower = word.lower()
        violations.append(Slop(
            rule="lexical.hammers",
            file=rel,
            line=entity.line,
            symbol=entity.name,
            message=(
                f"{entity.kind} `{entity.name}` matches hammer-word "
                f"`{word}` ({pos}); the term carries no semantic content."
                f"{_pervasiveness_note(word)}"
            ),
            severity=severity,
            metadata={
                "matched_word": word,
                "matched_position": pos,
                "kind": entity.kind,
                "language": entity.language,
                "token_spread": spread_map.get(token_lower, 0),
                "is_isolate": token_lower in isolate_tokens,
            },
        ))

    # 3. Module-name (file stem) check.
    seen_stems: set[str] = set()
    for file_path in lexicon.files():
        stem = Path(file_path).stem
        if not stem or stem in seen_stems:
            continue
        seen_stems.add(stem)
        items_analyzed += 1
        rel = _relfile(str(file_path))
        hit = _check_module_name(stem, by_word, rel, default_severity)
        if hit is None:
            continue
        word, severity = hit
        token_lower = word.lower()
        violations.append(Slop(
            rule="lexical.hammers",
            file=rel,
            line=1,
            symbol=stem,
            message=(
                f"module `{stem}` matches hammer-word `{word}` (module_name); "
                f"the term carries no semantic content."
                f"{_pervasiveness_note(word)}"
            ),
            severity=severity,
            metadata={
                "matched_word": word,
                "matched_position": "module_name",
                "kind": "module",
                "language": lexicon._language_by_path.get(str(file_path), "<unknown>"),
                "token_spread": spread_map.get(token_lower, 0),
                "is_isolate": token_lower in isolate_tokens,
            },
        ))

    return RuleResult(
        rule="lexical.hammers",
        status="fail" if violations else "pass",
        violations=violations,
        summary={
            "items_checked": items_analyzed,
            "terms_loaded": len(terms),
            "violation_count": len(violations),
        },
    )

RULE = RuleDefinition(
    name=Tag.HAMMERS.key,
    category=Tag.HAMMERS.key,
    description='Catchall vocabulary (Manager, Helper, Util, Spec) — one word for every nail',
    default_severity='warning',
    default_enabled=True,
    threshold_label='banlist match',
    run=run_hammers,
)
