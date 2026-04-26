"""Robert kernel - Robert C. Martin package design metrics."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from slop._structural.deps import FileDeps, deps_kernel

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PackageMetrics:
    """Robert C. Martin metrics for one package."""

    package: str                  # relative package path (display identity)
    path: str                     # abs filesystem path
    language: str
    files: int                    # count of source files in package
    ca: int                       # afferent coupling (packages that import this)
    ce: int                       # efferent coupling (packages this imports)
    instability: float | None     # Ce / (Ca + Ce); None if Ca+Ce == 0
    na: int                       # abstract type count
    nc: int                       # concrete type count
    abstractness: float | None    # Na / (Na + Nc); None if Na+Nc == 0
    distance: float | None        # |A + I - 1|; None if either is None
    zone: str                     # "pain"|"uselessness"|"warning"|"clean"|"ok"|"unknown"
    interpretation: str           # human-readable one-line verdict


@dataclass
class RobertResult:
    """Aggregated Robert C. Martin metrics result."""

    packages: list[PackageMetrics]   # sorted by distance desc (worst first)
    language: str
    packages_analyzed: int
    files_searched: int
    zone_counts: dict[str, int]      # {"pain": N, "uselessness": N, ...}
    guidance: list[str]              # per-problem action items
    errors: list[str] = field(default_factory=list)
    truncated: bool = False


# ---------------------------------------------------------------------------
# Language-specific globs and extensions
# ---------------------------------------------------------------------------

_LANG_GLOBS: dict[str, list[str]] = {
    "go": ["**/*.go"],
    "python": ["**/*.py"],
    "java": ["**/*.java"],
    "c_sharp": ["**/*.cs"],
    "typescript": ["**/*.ts", "**/*.tsx"],
    "javascript": ["**/*.js", "**/*.mjs", "**/*.cjs"],
    "rust": ["**/*.rs"],
    "julia": ["**/*.jl"],
}


# ---------------------------------------------------------------------------
# Main kernel entry point
# ---------------------------------------------------------------------------

def robert_kernel(
    root: Path,
    language: str,
    *,
    globs: list[str] | None = None,
    excludes: list[str] | None = None,
    hidden: bool = False,
    no_ignore: bool = False,
    max_results: int | None = None,
    include_main: bool = False,
) -> RobertResult:
    """Compute Robert C. Martin package design metrics.

    Args:
        root: Search root directory
        language: Language to analyze. One of: go, python, java, c_sharp,
            typescript, javascript, rust.
        globs: Additional include glob patterns
        excludes: Exclude glob patterns
        hidden: Include hidden files
        no_ignore: Don't respect gitignore
        max_results: Cap on packages in output
        include_main: Go only — include 'package main' packages

    Returns:
        RobertResult with per-package metrics sorted by distance desc.
    """
    language = language.lower()
    if language not in _LANG_GLOBS:
        return RobertResult(
            packages=[],
            language=language,
            packages_analyzed=0,
            files_searched=0,
            zone_counts=_empty_zone_counts(),
            guidance=[],
            errors=[
                f"Unsupported language '{language}'. Supported: "
                f"{', '.join(sorted(_LANG_GLOBS))}"
            ],
        )

    # Resolve effective globs
    lang_globs = list(_LANG_GLOBS[language])
    if globs:
        lang_globs = globs  # caller-specified globs override defaults

    # Step 1: Run deps_kernel to get file-level dependency information
    deps_result = deps_kernel(
        root=root,
        globs=lang_globs,
        excludes=excludes,
        target=None,
        language=language,
        hidden=hidden,
        no_ignore=no_ignore,
    )
    errors: list[str] = list(deps_result.errors)

    file_deps_list: list[FileDeps] = deps_result.files

    if not file_deps_list:
        return RobertResult(
            packages=[],
            language=language,
            packages_analyzed=0,
            files_searched=deps_result.files_searched,
            zone_counts=_empty_zone_counts(),
            guidance=[],
            errors=errors,
        )

    # Step 2: Group files into packages
    all_files = [Path(fd.file) for fd in file_deps_list]
    pkg_to_files = _resolve_packages(all_files, language)

    # Step 3: Filter out 'package main' packages in Go if include_main is False
    if language == "go" and not include_main:
        pkg_to_files = {
            pkg: files
            for pkg, files in pkg_to_files.items()
            if not _is_go_main_package(files)
        }

    if not pkg_to_files:
        return RobertResult(
            packages=[],
            language=language,
            packages_analyzed=0,
            files_searched=deps_result.files_searched,
            zone_counts=_empty_zone_counts(),
            guidance=[],
            errors=errors,
        )

    # Step 4: Build file → package map
    file_to_pkg: dict[str, str] = {}
    for pkg_dir, files in pkg_to_files.items():
        for f in files:
            file_to_pkg[str(f)] = pkg_dir

    # Step 5: Aggregate file-level coupling to package-level coupling
    pkg_ca: dict[str, set[str]] = {pkg: set() for pkg in pkg_to_files}
    pkg_ce: dict[str, set[str]] = {pkg: set() for pkg in pkg_to_files}

    for fd in file_deps_list:
        pkg_f = file_to_pkg.get(fd.file)
        if pkg_f is None:
            continue  # file not in a valid package (e.g. excluded main package)

        for importer_path in fd.imported_by:
            pkg_g = file_to_pkg.get(importer_path)
            if pkg_g is None:
                continue  # importer not in a valid package
            if pkg_g == pkg_f:
                continue  # same package, skip self-loops

            # pkg_g imports pkg_f → pkg_g contributes to Ca(pkg_f)
            pkg_ca[pkg_f].add(pkg_g)
            # pkg_f contributes to Ce(pkg_g)
            pkg_ce[pkg_g].add(pkg_f)

    # Step 6: Compute abstractness per package
    package_metrics_list: list[PackageMetrics] = []

    for pkg_dir, pkg_files in pkg_to_files.items():
        ca = len(pkg_ca.get(pkg_dir, set()))
        ce = len(pkg_ce.get(pkg_dir, set()))

        instability = _compute_instability(ca, ce)

        na, nc, abs_errors = _compute_abstractness(pkg_files, language)
        errors.extend(abs_errors)

        abstractness = _compute_abstractness_score(na, nc)
        distance = _compute_distance(instability, abstractness)
        zone = _compute_zone(instability, abstractness, distance)
        interpretation = _interpret(instability, abstractness, distance, zone)

        rel_pkg = _relative_path(root, Path(pkg_dir))

        package_metrics_list.append(PackageMetrics(
            package=rel_pkg,
            path=pkg_dir,
            language=language,
            files=len(pkg_files),
            ca=ca,
            ce=ce,
            instability=instability,
            na=na,
            nc=nc,
            abstractness=abstractness,
            distance=distance,
            zone=zone,
            interpretation=interpretation,
        ))

    # Step 7: Sort by distance descending (worst first), then by package name for stability
    package_metrics_list.sort(
        key=lambda pm: (-(pm.distance if pm.distance is not None else -1.0), pm.package)
    )

    # Step 8: Apply max_results cap
    truncated = False
    if max_results is not None and len(package_metrics_list) > max_results:
        package_metrics_list = package_metrics_list[:max_results]
        truncated = True

    # Step 9: Zone counts and guidance
    zone_counts = _count_zones(package_metrics_list)
    guidance = _build_guidance(package_metrics_list)

    return RobertResult(
        packages=package_metrics_list,
        language=language,
        packages_analyzed=len(package_metrics_list),
        files_searched=deps_result.files_searched,
        zone_counts=zone_counts,
        guidance=guidance,
        errors=errors,
        truncated=truncated,
    )


# ---------------------------------------------------------------------------
# Package resolution
# ---------------------------------------------------------------------------

def _resolve_packages(files: list[Path], language: str) -> dict[str, list[Path]]:
    """Group files into packages by language-specific rules.

    Go:     directory → package (all .go files in same dir)
    Python: directory → package only if __init__.py present

    Returns: {abs_dir_str: [file_paths]}
    """
    by_dir: dict[str, list[Path]] = {}
    for f in files:
        d = str(f.parent)
        by_dir.setdefault(d, []).append(f)

    if language == "go":
        return by_dir

    if language == "python":
        result: dict[str, list[Path]] = {}
        for d, dir_files in by_dir.items():
            dir_path = Path(d)
            if (dir_path / "__init__.py").exists():
                result[d] = dir_files
        return result

    return by_dir


def _is_go_main_package(files: list[Path]) -> bool:
    """Return True if any Go file in the list declares 'package main'."""
    pkg_pattern = re.compile(r"^\s*package\s+main\b")
    for f in files:
        try:
            # Only read first 20 lines for performance
            content = f.read_text(encoding="utf-8", errors="replace")
            for line in content.splitlines()[:20]:
                if pkg_pattern.match(line):
                    return True
        except Exception:
            pass
    return False


# ---------------------------------------------------------------------------
# Abstractness computation
# ---------------------------------------------------------------------------

# Tree-sitter queries per language
_GO_INTERFACE_QUERY = """
(type_declaration
  (type_spec
    name: (type_identifier) @name
    type: (interface_type))) @abstract
"""

_GO_STRUCT_QUERY = """
(type_declaration
  (type_spec
    name: (type_identifier) @name
    type: (struct_type))) @concrete
"""

_PYTHON_CLASS_QUERY = """
(class_definition
  name: (identifier) @name
  superclasses: (argument_list)? @bases) @class
"""

_ABSTRACT_BASE_PATTERN = re.compile(r"\b(ABC|Protocol|ABCMeta)\b")

# --- Java ---
_JAVA_INTERFACE_QUERY = """
(interface_declaration name: (identifier) @name)
"""
_JAVA_CLASS_QUERY = """
(class_declaration
  (modifiers)? @mods
  name: (identifier) @name)
"""
_JAVA_RECORD_QUERY = """
(record_declaration name: (identifier) @name)
"""

# --- C# ---
_CSHARP_INTERFACE_QUERY = """
(interface_declaration name: (identifier) @name)
"""
_CSHARP_CLASS_QUERY = """
(class_declaration name: (identifier) @name) @class
"""
_CSHARP_STRUCT_QUERY = """
(struct_declaration name: (identifier) @name)
"""
_CSHARP_RECORD_QUERY = """
(record_declaration name: (identifier) @name)
"""

# --- TypeScript ---
_TS_INTERFACE_QUERY = """
(interface_declaration name: (type_identifier) @name)
"""
_TS_CLASS_QUERY = """
(class_declaration name: (type_identifier) @name) @class
"""
_TS_ABSTRACT_CLASS_QUERY = """
(abstract_class_declaration name: (type_identifier) @name)
"""

# --- JavaScript ---
_JS_CLASS_QUERY = """
(class_declaration name: (identifier) @name)
"""

# --- Rust ---
_RUST_TRAIT_QUERY = """
(trait_item name: (type_identifier) @name)
"""
_RUST_STRUCT_QUERY = """
(struct_item name: (type_identifier) @name)
"""
_RUST_ENUM_QUERY = """
(enum_item name: (type_identifier) @name)
"""

# Text-tier fallback regexes
_GO_INTERFACE_RE = re.compile(r"^type\s+\w+\s+interface\b", re.MULTILINE)
_GO_STRUCT_RE = re.compile(r"^type\s+\w+\s+struct\b", re.MULTILINE)
_PYTHON_ABSTRACT_RE = re.compile(r"^class\s+\w+\s*\(.*(?:ABC|Protocol|ABCMeta)", re.MULTILINE)
_PYTHON_CONCRETE_RE = re.compile(r"^class\s+\w+", re.MULTILINE)

# Java: interfaces are always abstract; classes are abstract only with the
# `abstract` modifier. Records are concrete. Order-tolerant modifier scanning
# via two regexes (abstract-class then all-class) and subtracting.
_JAVA_INTERFACE_RE = re.compile(
    r"^\s*(?:public|private|protected|static|final|sealed|non-sealed|\s)*\binterface\s+\w+",
    re.MULTILINE,
)
_JAVA_ABSTRACT_CLASS_RE = re.compile(
    r"^\s*(?:(?:public|private|protected|static|final|sealed|non-sealed)\s+)*abstract(?:\s+(?:public|private|protected|static|final|sealed|non-sealed))*\s+class\s+\w+",
    re.MULTILINE,
)
_JAVA_CLASS_RE = re.compile(
    r"^\s*(?:public|private|protected|abstract|static|final|sealed|non-sealed|\s)*\bclass\s+\w+",
    re.MULTILINE,
)
_JAVA_RECORD_RE = re.compile(r"^\s*(?:public|private|protected|\s)*\brecord\s+\w+", re.MULTILINE)

# C#: same shape as Java. `sealed` / `static` / `partial` etc. are modifiers
# that don't affect abstractness; only `abstract` does.
_CSHARP_INTERFACE_RE = re.compile(
    r"^\s*(?:public|private|protected|internal|static|\s)*\binterface\s+\w+",
    re.MULTILINE,
)
_CSHARP_ABSTRACT_CLASS_RE = re.compile(
    r"^\s*(?:(?:public|private|protected|internal|static|sealed|partial)\s+)*abstract(?:\s+(?:public|private|protected|internal|static|sealed|partial))*\s+class\s+\w+",
    re.MULTILINE,
)
_CSHARP_CLASS_RE = re.compile(
    r"^\s*(?:public|private|protected|internal|abstract|static|sealed|partial|\s)*\bclass\s+\w+",
    re.MULTILINE,
)
_CSHARP_STRUCT_RE = re.compile(
    r"^\s*(?:public|private|protected|internal|readonly|ref|\s)*\bstruct\s+\w+",
    re.MULTILINE,
)
_CSHARP_RECORD_RE = re.compile(
    r"^\s*(?:public|private|protected|internal|\s)*\brecord\s+\w+", re.MULTILINE
)

# TypeScript: interface, abstract class (prefixed with `abstract`), plain class.
_TS_INTERFACE_RE = re.compile(
    r"^\s*(?:export\s+|declare\s+)*interface\s+\w+", re.MULTILINE
)
_TS_ABSTRACT_CLASS_RE = re.compile(
    r"^\s*(?:export\s+|declare\s+)*abstract\s+class\s+\w+", re.MULTILINE
)
_TS_CLASS_RE = re.compile(
    r"^\s*(?:export\s+|declare\s+|abstract\s+)*class\s+\w+", re.MULTILINE
)

# JavaScript: no abstract / interface concept in the language itself, so every
# class declaration is treated as concrete.
_JS_CLASS_RE = re.compile(r"^\s*(?:export\s+|default\s+)*class\s+\w+", re.MULTILINE)

# Rust: trait is abstract; struct and enum are concrete.
_RUST_TRAIT_RE = re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:unsafe\s+)?trait\s+\w+", re.MULTILINE)
_RUST_STRUCT_RE = re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?struct\s+\w+", re.MULTILINE)
_RUST_ENUM_RE = re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?enum\s+\w+", re.MULTILINE)


def _compute_abstractness(
    pkg_files: list[Path],
    language: str,
) -> tuple[int, int, list[str]]:
    """Count abstract and concrete types in a package.

    Returns (na, nc, errors).
    """
    errors: list[str] = []

    try:
        return _compute_abstractness_ast(pkg_files, language, errors)
    except Exception as e:
        errors.append(f"AST abstractness failed, using regex fallback: {e}")

    return _compute_abstractness_text(pkg_files, language, errors)


def _count_query_matches(
    pkg_files: list[Path],
    query_str: str,
    language: str,
    errors: list[str],
) -> int:
    """Run a tree-sitter query over pkg_files and count distinct @name captures."""
    from slop._ast.query import query_kernel

    res = query_kernel(files=pkg_files, query_str=query_str, language=language)
    errors.extend(res.errors)
    names: set[str] = set()
    for match in res.matches:
        for cap in match.captures:
            if cap.name == "name":
                names.add(f"{match.file}:{cap.text}:{cap.line}")
    return len(names)


def _split_classes_by_abstract_modifier(
    pkg_files: list[Path],
    query_str: str,
    language: str,
    errors: list[str],
    modifier_capture: str = "mods",
) -> tuple[int, int]:
    """Run a class-declaration query and split captures by whether the
    modifier-capture text contains ``abstract``.

    Returns ``(abstract_count, concrete_count)``. Classes without the captured
    modifiers field are treated as concrete.
    """
    from slop._ast.query import query_kernel

    res = query_kernel(files=pkg_files, query_str=query_str, language=language)
    errors.extend(res.errors)

    abstract_count = 0
    concrete_count = 0
    for ast_match in res.matches:
        caps_by_name: dict[str, list[str]] = {}
        for cap in ast_match.captures:
            caps_by_name.setdefault(cap.name, []).append(cap.text)
        if "name" not in caps_by_name:
            continue
        mods_texts = caps_by_name.get(modifier_capture, [])
        is_abstract = any(re.search(r"\babstract\b", m) for m in mods_texts)
        if is_abstract:
            abstract_count += 1
        else:
            concrete_count += 1
    return abstract_count, concrete_count


def _compute_abstractness_ast(
    pkg_files: list[Path],
    language: str,
    errors: list[str],
) -> tuple[int, int, list[str]]:
    """Count types using tree-sitter AST."""
    from slop._ast.query import query_kernel

    na = 0
    nc = 0

    if language == "go":
        na = _count_query_matches(pkg_files, _GO_INTERFACE_QUERY, "go", errors)
        nc = _count_query_matches(pkg_files, _GO_STRUCT_QUERY, "go", errors)

    elif language == "python":
        res = query_kernel(files=pkg_files, query_str=_PYTHON_CLASS_QUERY, language="python")
        errors.extend(res.errors)
        for ast_match in res.matches:
            caps_by_name: dict[str, list[str]] = {}
            for cap in ast_match.captures:
                caps_by_name.setdefault(cap.name, []).append(cap.text)

            bases_texts = caps_by_name.get("bases", [])
            is_abstract = any(_ABSTRACT_BASE_PATTERN.search(b) for b in bases_texts)
            if is_abstract:
                na += 1
            else:
                nc += 1

    elif language == "java":
        na += _count_query_matches(pkg_files, _JAVA_INTERFACE_QUERY, "java", errors)
        java_abstract, java_concrete = _split_classes_by_abstract_modifier(
            pkg_files, _JAVA_CLASS_QUERY, "java", errors,
        )
        na += java_abstract
        nc += java_concrete
        nc += _count_query_matches(pkg_files, _JAVA_RECORD_QUERY, "java", errors)

    elif language == "c_sharp":
        na += _count_query_matches(pkg_files, _CSHARP_INTERFACE_QUERY, "c_sharp", errors)
        cs_abstract, cs_concrete = _split_classes_by_abstract_modifier(
            pkg_files, _CSHARP_CLASS_QUERY, "c_sharp", errors,
            # C# class_declaration places `abstract` as a sibling @class modifier;
            # capture the whole class node's source and scan it for the keyword.
            modifier_capture="class",
        )
        na += cs_abstract
        nc += cs_concrete
        nc += _count_query_matches(pkg_files, _CSHARP_STRUCT_QUERY, "c_sharp", errors)
        nc += _count_query_matches(pkg_files, _CSHARP_RECORD_QUERY, "c_sharp", errors)

    elif language == "typescript":
        na += _count_query_matches(pkg_files, _TS_INTERFACE_QUERY, "typescript", errors)
        na += _count_query_matches(pkg_files, _TS_ABSTRACT_CLASS_QUERY, "typescript", errors)
        # Non-abstract classes. If the grammar lacks a separate abstract_class_declaration
        # node, the @class capture catches both and we fall back to text scan.
        ts_abstract, ts_concrete = _split_classes_by_abstract_modifier(
            pkg_files, _TS_CLASS_QUERY, "typescript", errors,
            modifier_capture="class",
        )
        na += ts_abstract
        nc += ts_concrete

    elif language == "javascript":
        # JS has no interface or abstract-class in the language; treat every
        # class declaration as concrete. Packages with Ca > 0 and no abstraction
        # will legitimately land in Zone of Pain.
        nc = _count_query_matches(pkg_files, _JS_CLASS_QUERY, "javascript", errors)

    elif language == "rust":
        na = _count_query_matches(pkg_files, _RUST_TRAIT_QUERY, "rust", errors)
        nc += _count_query_matches(pkg_files, _RUST_STRUCT_QUERY, "rust", errors)
        nc += _count_query_matches(pkg_files, _RUST_ENUM_QUERY, "rust", errors)

    else:
        return _compute_abstractness_text(pkg_files, language, errors)

    return na, nc, errors


def _compute_abstractness_text(
    pkg_files: list[Path],
    language: str,
    errors: list[str],
) -> tuple[int, int, list[str]]:
    """Count types using text-tier regex fallback."""
    na = 0
    nc = 0

    for f in pkg_files:
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            errors.append(f"{f}: read error: {e}")
            continue

        if language == "go":
            na += len(_GO_INTERFACE_RE.findall(content))
            nc += len(_GO_STRUCT_RE.findall(content))

        elif language == "python":
            abstract_matches = set(_PYTHON_ABSTRACT_RE.findall(content))
            all_classes = _PYTHON_CONCRETE_RE.findall(content)
            na += len(abstract_matches)
            nc += max(0, len(all_classes) - len(abstract_matches))

        elif language == "java":
            na += len(_JAVA_INTERFACE_RE.findall(content))
            abstract_classes = len(_JAVA_ABSTRACT_CLASS_RE.findall(content))
            all_classes = len(_JAVA_CLASS_RE.findall(content))
            na += abstract_classes
            nc += max(0, all_classes - abstract_classes)
            nc += len(_JAVA_RECORD_RE.findall(content))

        elif language == "c_sharp":
            na += len(_CSHARP_INTERFACE_RE.findall(content))
            abstract_classes = len(_CSHARP_ABSTRACT_CLASS_RE.findall(content))
            all_classes = len(_CSHARP_CLASS_RE.findall(content))
            na += abstract_classes
            nc += max(0, all_classes - abstract_classes)
            nc += len(_CSHARP_STRUCT_RE.findall(content))
            nc += len(_CSHARP_RECORD_RE.findall(content))

        elif language == "typescript":
            na += len(_TS_INTERFACE_RE.findall(content))
            abstract_classes = len(_TS_ABSTRACT_CLASS_RE.findall(content))
            all_classes = len(_TS_CLASS_RE.findall(content))
            na += abstract_classes
            nc += max(0, all_classes - abstract_classes)

        elif language == "javascript":
            nc += len(_JS_CLASS_RE.findall(content))

        elif language == "rust":
            na += len(_RUST_TRAIT_RE.findall(content))
            nc += len(_RUST_STRUCT_RE.findall(content))
            nc += len(_RUST_ENUM_RE.findall(content))

    return na, nc, errors


# ---------------------------------------------------------------------------
# Metric formulas
# ---------------------------------------------------------------------------

def _compute_instability(ca: int, ce: int) -> float | None:
    """Ce / (Ca + Ce); None if Ca+Ce == 0."""
    total = ca + ce
    if total == 0:
        return None
    return ce / total


def _compute_abstractness_score(na: int, nc: int) -> float | None:
    """Na / (Na + Nc); None if Na+Nc == 0."""
    total = na + nc
    if total == 0:
        return None
    return na / total


def _compute_distance(i: float | None, a: float | None) -> float | None:
    """|A + I - 1|; None if either is None."""
    if i is None or a is None:
        return None
    return abs(a + i - 1.0)


def _compute_zone(i: float | None, a: float | None, d: float | None) -> str:
    """Classify package into a zone.

    pain:        I < 0.3 AND A < 0.3
    uselessness: I > 0.7 AND A > 0.7
    warning:     D' >= 0.5 (not in above zones)
    clean:       D' < 0.2
    ok:          everything else
    unknown:     when I or A is None
    """
    if i is None or a is None:
        return "unknown"
    if i < 0.3 and a < 0.3:
        return "pain"
    if i > 0.7 and a > 0.7:
        return "uselessness"
    if d is not None and d >= 0.5:
        return "warning"
    if d is not None and d < 0.2:
        return "clean"
    return "ok"


def _interpret(
    i: float | None,
    a: float | None,
    d: float | None,
    zone: str,
) -> str:
    """Generate a human-readable one-line verdict for a package."""
    i_str = f"{i:.2f}" if i is not None else "N/A"
    a_str = f"{a:.2f}" if a is not None else "N/A"
    d_str = f"{d:.2f}" if d is not None else "N/A"

    if zone == "pain":
        return (
            f"Zone of Pain — stable (I={i_str}) but concrete (A={a_str}). "
            f"Rigid under changing requirements. Consider extracting interfaces to allow "
            f"substitution, or accept the stability contract explicitly."
        )
    if zone == "uselessness":
        return (
            f"Zone of Uselessness — abstract (A={a_str}) but unstable (I={i_str}). "
            f"Highly abstract with few dependents. Collapse abstractions or invert "
            f"dependencies to gain stability."
        )
    if zone == "warning":
        return (
            f"Drifting from main sequence (D'={d_str}). "
            f"Abstractness ({a_str}) is disproportionate to instability ({i_str}). "
            f"Reduce abstractions or accept more incoming dependencies."
        )
    if zone == "clean":
        return (
            f"On main sequence (D'={d_str}). Abstractness and stability "
            f"are proportional — no action needed."
        )
    if zone == "unknown":
        return (
            "Insufficient data — no type declarations found (Na+Nc=0) or no "
            "import edges (Ca+Ce=0). Cannot compute I or A."
        )
    # ok
    return (
        f"Acceptable (D'={d_str}, I={i_str}, A={a_str}). "
        f"Minor drift from main sequence — monitor but no action required."
    )


# ---------------------------------------------------------------------------
# Guidance and zone counting
# ---------------------------------------------------------------------------

_ZONE_LABELS: dict[str, str] = {
    "pain": "Zone of Pain",
    "uselessness": "Zone of Uselessness",
    "warning": "Warning",
}

_ZONE_ACTIONS: dict[str, str] = {
    "pain": "Extract interfaces from structs or invert dependencies to reduce Ca.",
    "uselessness": "Collapse abstractions or invert dependencies to gain stability.",
    "warning": "Reduce abstract types or accept more incoming dependencies.",
}


def _build_guidance(packages: list[PackageMetrics]) -> list[str]:
    """Build guidance list — one entry per non-clean, non-ok package."""
    items: list[str] = []
    for pm in packages:
        if pm.zone not in _ZONE_LABELS:
            continue
        label = _ZONE_LABELS[pm.zone]
        action = _ZONE_ACTIONS.get(pm.zone, "Review this package.")
        i_str = f"{pm.instability:.2f}" if pm.instability is not None else "N/A"
        a_str = f"{pm.abstractness:.2f}" if pm.abstractness is not None else "N/A"
        items.append(f"{pm.package} ({label}): I={i_str}, A={a_str}. {action}")
    return items


def _count_zones(packages: list[PackageMetrics]) -> dict[str, int]:
    """Count packages per zone."""
    zones = ("pain", "uselessness", "warning", "clean", "ok", "unknown")
    counts: dict[str, int] = {z: 0 for z in zones}
    for pm in packages:
        counts[pm.zone] = counts.get(pm.zone, 0) + 1
    return counts


def _empty_zone_counts() -> dict[str, int]:
    return {"pain": 0, "uselessness": 0, "warning": 0, "clean": 0, "ok": 0, "unknown": 0}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _relative_path(root: Path, path: Path) -> str:
    """Return relative path string, or abs path if not relative to root."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


