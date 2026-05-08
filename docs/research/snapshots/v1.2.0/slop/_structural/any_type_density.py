"""Any-type density kernel.

Detects the fraction of type annotations in each file that use the language's
"universal escape hatch" type — the annotation that defeats the purpose of
having a type system at all.

Per-language escape-hatch tokens
---------------------------------
  Python        ``Any`` (typing.Any)
  Go            ``interface{}`` / ``any`` (Go 1.18+)
  TypeScript    ``any``  (also ``unknown`` when used unsafely)
  JavaScript    ``any`` (JSDoc type)
  Rust          (no direct equivalent; dyn Any / Box<dyn Any> counted)
  Java          ``Object`` as a parameter or return annotation
  C#            ``object``, ``dynamic``
  Julia         ``Any`` type annotation

Two-pass strategy
-----------------
1. **Escape pass**: ripgrep for escape-hatch patterns → per-file escape count.
2. **Annotation pass**: ripgrep for general type-annotation syntax → per-file
   total annotation count.
3. Density = escape / total (skipped when total == 0).

Files where density exceeds ``threshold`` are flagged.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from slop._text.grep import grep_kernel

# ---------------------------------------------------------------------------
# Per-language patterns
# ---------------------------------------------------------------------------

# (escape_pattern, annotation_pattern, globs)
#
# Ruby is intentionally NOT registered. Ruby is dynamically typed —
# every parameter is implicitly ``Object``, every return is implicit,
# and there are no type-annotation patterns to count. The rule's
# premise (fraction of type annotations using an escape-hatch type)
# has no meaningful definition. Same posture as CK on C (no class
# concept) — silent no-op via missing registration.
_LANG_CONFIG: dict[str, tuple[str, str, list[str]]] = {
    "python": (
        r"\bAny\b",
        r"(?:->|:\s)[A-Za-z_\[\]|, ]+",
        ["**/*.py"],
    ),
    "typescript": (
        r":\s*any\b",
        r":\s*[A-Za-z_][A-Za-z0-9_\[\]|<>, ]*",
        ["**/*.ts", "**/*.tsx"],
    ),
    "javascript": (
        r"@type\s*\{any\}",
        r"@type\s*\{[^\}]+\}",
        ["**/*.js", "**/*.mjs", "**/*.cjs"],
    ),
    "go": (
        r"(?:interface\{\}|\bany\b)",
        r"(?:func\b|var\b|\btype\b|\bmap\[)",
        ["**/*.go"],
    ),
    "rust": (
        r"dyn\s+Any\b",
        r"(?:fn\s+\w+\s*\(|:\s*(?:Box|Vec|Arc|Rc|Option|Result)<)",
        ["**/*.rs"],
    ),
    "java": (
        r"\bObject\b(?:\s*[,\)]|\s*\{|\s*throws)",
        r"(?:public|private|protected|static)\s+\w+\s+\w+\s*\(",
        ["**/*.java"],
    ),
    "c_sharp": (
        r"\b(?:object|dynamic)\b",
        r"(?:public|private|protected|internal|static)\s+(?:\w+[\[\]?]*\s+){1,3}\w+\s*[({]",
        ["**/*.cs"],
    ),
    "julia": (
        r"::\s*Any\b",
        r"::[A-Za-z_]\w*",
        ["**/*.jl"],
    ),
    # C has no parametric "Any" type. ``void *`` is the universal escape
    # hatch — opaque pointer that defeats the type checker. The
    # annotation regex matches type-prefixed declarations (parameters,
    # variable declarations, function returns); calibration is tentative
    # and may flag noisily on macro-heavy or const-laden codebases.
    # Default severity = "warning"; see docs/C.md.
    "c": (
        r"\bvoid\s*\*",
        r"(?:^|[\s,(])"
        r"(?:const\s+|register\s+|volatile\s+|restrict\s+|"
        r"static\s+|extern\s+|inline\s+|auto\s+)*"
        r"(?:unsigned\s+|signed\s+)?"
        r"(?:int|char|float|double|long|short|void|size_t|ssize_t|"
        r"int\d{1,2}_t|uint\d{1,2}_t|ptrdiff_t|"
        r"struct\s+\w+|enum\s+\w+|union\s+\w+|"
        r"[A-Z]\w*_t|[A-Z]\w*)"
        r"\s*\*?\s*\w+\s*[,;()=\[]",
        ["**/*.c", "**/*.h"],
    ),
    # C++ extends C's escape hatches: ``void *`` plus ``std::any``
    # (C++17). Annotation pattern adds C++ qualifiers, references via
    # ``&``, and namespaced/templated types. Calibration is tentative.
    "cpp": (
        r"\bvoid\s*\*|\bstd::any\b",
        r"(?:^|[\s,(])"
        r"(?:const\s+|volatile\s+|static\s+|extern\s+|inline\s+|"
        r"constexpr\s+|consteval\s+|mutable\s+|"
        r"register\s+|restrict\s+|auto\s+)*"
        r"(?:unsigned\s+|signed\s+)?"
        r"(?:int|char|float|double|long|short|void|bool|"
        r"size_t|ssize_t|int\d{1,2}_t|uint\d{1,2}_t|ptrdiff_t|"
        r"struct\s+\w+|enum\s+\w+|union\s+\w+|class\s+\w+|"
        r"[A-Z]\w*_t|std::\w+(?:<[^>]*>)?|[A-Z]\w*(?:<[^>]*>)?)"
        r"\s*[*&]?\s*\w+\s*[,;()=\[{]",
        ["**/*.cpp", "**/*.cc", "**/*.cxx", "**/*.hpp", "**/*.hxx"],
    ),
}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class AnyTypeDensityEntry:
    """One file that exceeded the any-type density threshold."""

    file: str           # relative path
    language: str
    escape_count: int   # annotations using the escape-hatch type
    total_count: int    # total type annotations detected
    density: float      # escape / total


@dataclass
class AnyTypeDensityResult:
    """Aggregated result from any_type_density_kernel."""

    entries: list[AnyTypeDensityEntry] = field(default_factory=list)
    files_searched: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public kernel
# ---------------------------------------------------------------------------


def any_type_density_kernel(
    root: Path,
    *,
    languages: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
) -> AnyTypeDensityResult:
    """Compute escape-hatch type density per file.

    Args:
        root:      Search root.
        languages: Restrict to these languages (default: all supported).
        excludes:  Exclude patterns.
        hidden:    Search hidden files.
        no_ignore: Ignore .gitignore rules.
    """
    active_langs = (
        {l.lower() for l in languages} & set(_LANG_CONFIG)
        if languages else set(_LANG_CONFIG)
    )

    # Accumulate: file → {"escape": int, "total": int, "lang": str}
    file_stats: dict[str, dict] = defaultdict(lambda: {"escape": 0, "total": 0, "lang": "unknown"})
    errors: list[str] = []
    files_seen: set[str] = set()

    for lang in sorted(active_langs):
        escape_pat, annot_pat, globs = _LANG_CONFIG[lang]
        exc = excludes or []

        # Escape pass
        escape_result = grep_kernel(
            patterns=[{"kind": "regex", "value": escape_pat}],
            root=root,
            globs=globs,
            excludes=exc,
            hidden=hidden,
            no_ignore=no_ignore,
        )
        errors.extend(escape_result.errors)
        for m in escape_result.matches:
            file_stats[m.path]["escape"] += 1
            file_stats[m.path]["lang"] = lang
            files_seen.add(m.path)

        # Annotation pass
        annot_result = grep_kernel(
            patterns=[{"kind": "regex", "value": annot_pat}],
            root=root,
            globs=globs,
            excludes=exc,
            hidden=hidden,
            no_ignore=no_ignore,
        )
        errors.extend(annot_result.errors)
        for m in annot_result.matches:
            file_stats[m.path]["total"] += 1
            file_stats[m.path]["lang"] = lang
            files_seen.add(m.path)

    entries: list[AnyTypeDensityEntry] = []
    for rel_path, stats in file_stats.items():
        escape = stats["escape"]
        total = stats["total"]
        if total == 0:
            continue
        density = escape / total
        entries.append(AnyTypeDensityEntry(
            file=rel_path,
            language=stats["lang"],
            escape_count=escape,
            total_count=total,
            density=round(density, 4),
        ))

    entries.sort(key=lambda e: -e.density)
    return AnyTypeDensityResult(
        entries=entries,
        files_searched=len(files_seen),
        errors=errors,
    )
