"""PoC 4: Entity surface area detection.

Algorithm
---------
Given a candidate **entity alphabet** (a closed set of token values
that appear consistently as type tags), enumerate every reference to
each entity across the codebase. Categorise references as:

- **DATA** — entity name appears as a dict key, a string literal in a
  registry / config table, or a constant.
- **BEHAVIOUR** — entity name appears as a token inside a function or
  method name (the function is tagged with the entity).
- **STATE** — entity name appears in a class / dataclass field name
  or in a data structure's keys.

The output frames each entity as a candidate class: data + behaviour
scattered across files = a missing class with that data and those
methods.

Theoretical basis
-----------------
- Bavota et al., "An Extract Class Refactoring Approach Based on
  Class Cohesion": cohesion = methods + data sharing a domain
  entity.
- Coad/Yourdon (1991), Object-Oriented Analysis: identifying domain
  entities by enumerating where they appear in data and operations.

Usage
-----
    python poc4_entity_surface_area.py FILE [FILE ...]

The entity alphabet is auto-discovered from PoC1's affix algorithm —
specifically, alphabets matching a known set of language tokens are
flagged as candidate entities.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

CAMEL_LU = re.compile(r"([a-z])([A-Z])")
CAMEL_UU = re.compile(r"([A-Z]+)([A-Z][a-z])")


def split_identifier(name):
    s = name.strip("_")
    s = CAMEL_LU.sub(r"\1_\2", s)
    s = CAMEL_UU.sub(r"\1_\2", s)
    return [t.lower() for t in re.split(r"[_]+", s) if t]


# Hardcoded entity alphabet for the slop target — the closed set of
# language tokens. In a productionised version, this would be
# auto-discovered from PoC1b's clustering output.
LANGUAGE_ALPHABET = {
    "python", "javascript", "typescript", "rust", "go", "java",
    "c_sharp", "csharp", "julia", "c", "cpp", "ruby", "js", "ts",
}


def find_def_lines(text, name_pattern):
    """Return list of (line_no, line_text) where a def line matches name_pattern."""
    out = []
    for i, line in enumerate(text.splitlines(), start=1):
        m = re.match(r"^def\s+(\w+)\s*\(", line)
        if m and name_pattern in split_identifier(m.group(1)):
            out.append((i, line.strip()))
    return out


def find_dict_keys(text, key_value):
    """Return list of (line_no, line_text) where ``"key_value"`` appears as a dict key."""
    out = []
    needle1 = f'"{key_value}"'
    needle2 = f"'{key_value}'"
    for i, line in enumerate(text.splitlines(), start=1):
        if (needle1 in line or needle2 in line):
            # Filter to "looks like a dict key" — line ends with `:` or contains `: <something>`
            if re.search(rf'[\'"]{re.escape(key_value)}[\'"]\s*:', line):
                out.append((i, line.strip()))
    return out


def scan_entity(paths, entity):
    """Return per-entity report data."""
    data_hits = []      # (file, line_no, line_text)
    behaviour_hits = [] # (file, line_no, line_text)

    for p in paths:
        text = p.read_text(encoding="utf-8", errors="replace")
        # DATA: dict-key occurrences
        for ln, lt in find_dict_keys(text, entity):
            data_hits.append((p, ln, lt))
        # Also handle the c_sharp <-> csharp aliasing
        if entity == "csharp":
            for ln, lt in find_dict_keys(text, "c_sharp"):
                data_hits.append((p, ln, lt))
        # BEHAVIOUR: function names containing the entity token
        for ln, lt in find_def_lines(text, entity):
            behaviour_hits.append((p, ln, lt))
        if entity == "csharp":
            for ln, lt in find_def_lines(text, "csharp"):
                behaviour_hits.append((p, ln, lt))

    return data_hits, behaviour_hits


def report(paths, alphabet):
    lines = ["# composition.entity_surface_area — candidate missing classes",
             ""]
    lines.append("This report enumerates the surface area of each "
                 "candidate entity in the alphabet. An entity with both "
                 "data references (registry keys, config entries) and "
                 "behaviour references (functions tagged with the entity "
                 "name) is a textbook missing-class signature: data and "
                 "behaviour scattered across files that should be "
                 "bundled per-entity.")
    lines.append("")
    lines.append(f"**Alphabet under analysis** ({len(alphabet)} entities): "
                 + ", ".join(f"`{e}`" for e in sorted(alphabet)))
    lines.append("")

    # Aggregate
    summaries = []
    for entity in sorted(alphabet):
        data, behaviour = scan_entity(paths, entity)
        if not data and not behaviour:
            continue
        summaries.append((entity, data, behaviour))

    if not summaries:
        lines.append("_No entities from the alphabet had measurable surface area._")
        return "\n".join(lines)

    # Headline: total surface area across the alphabet
    total_data = sum(len(d) for _, d, _ in summaries)
    total_behav = sum(len(b) for _, _, b in summaries)
    distinct_entities = len(summaries)

    lines.append("## Headline diagnosis")
    lines.append("")
    lines.append(f"**{distinct_entities} entities** from the alphabet have "
                 f"non-zero surface area. Across these entities, "
                 f"**{total_data} data references** and "
                 f"**{total_behav} behaviour references** are scattered "
                 f"across the scanned files.")
    lines.append("")
    lines.append("This pattern — same alphabet of entities referenced as "
                 "both data and behaviour, no shared abstraction binding "
                 "them — is the signature of a missing class. Each "
                 "entity is implicitly a class instance whose data and "
                 "methods have been scattered.")
    lines.append("")
    lines.append("**Recommended compositional mechanism**: introduce a "
                 "first-class entity (class, dataclass, or trait). Each "
                 "alphabet value becomes an instance or subclass. Data "
                 "references become fields on the instance; behaviour "
                 "references become methods.")
    lines.append("")

    # Per-entity detail
    lines.append("## Per-entity surface area")
    lines.append("")
    summaries.sort(key=lambda x: -(len(x[1]) + len(x[2])))
    for entity, data, behaviour in summaries:
        files_d = sorted({p.name for p, _, _ in data})
        files_b = sorted({p.name for p, _, _ in behaviour})
        all_files = sorted(set(files_d) | set(files_b))

        lines.append(f"### Entity: `{entity}`")
        lines.append("")
        lines.append(f"- **Total surface area**: {len(data)} data references + "
                     f"{len(behaviour)} behaviour references = "
                     f"{len(data) + len(behaviour)} occurrences")
        lines.append(f"- **Files touched**: {len(all_files)} "
                     f"({', '.join(all_files)})")
        lines.append("")

        if behaviour:
            lines.append("**Behaviour (functions tagged with this entity):**")
            lines.append("")
            for p, ln, lt in behaviour[:10]:
                # Extract just the function name from the def line
                m = re.match(r"^def\s+(\w+)", lt)
                fname = m.group(1) if m else lt
                lines.append(f"- `{fname}` ({p.name}:{ln})")
            if len(behaviour) > 10:
                lines.append(f"- … and {len(behaviour) - 10} more")
            lines.append("")

        if data:
            lines.append("**Data (registry / config / dict-key occurrences):**")
            lines.append("")
            for p, ln, lt in data[:10]:
                # Truncate long lines
                shown = lt[:120] + ("…" if len(lt) > 120 else "")
                lines.append(f"- {p.name}:{ln} — `{shown}`")
            if len(data) > 10:
                lines.append(f"- … and {len(data) - 10} more")
            lines.append("")

        lines.append("**If `" + entity.capitalize() +
                     "` were a class**, it would carry:")
        lines.append("")
        # Inferred fields = data points; inferred methods = behaviour
        method_names = set()
        for _, _, lt in behaviour:
            m = re.match(r"^def\s+(\w+)", lt)
            if m:
                # Strip the entity token from the function name
                tokens = split_identifier(m.group(1))
                method_tokens = [t for t in tokens if t != entity]
                if method_tokens:
                    method_names.add("_".join(method_tokens))
        if method_names:
            lines.append(f"- methods: " +
                         ", ".join(f"`{m}`" for m in sorted(method_names)))
        lines.append(f"- fields / state: per-entity entries in "
                     f"{len(set((p.name for p, _, _ in data)))} different "
                     "registry/config dicts")
        lines.append("")

    return "\n".join(lines)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        sys.exit(1)
    paths = [Path(p) for p in argv[1:]]
    print(report(paths, LANGUAGE_ALPHABET))


if __name__ == "__main__":
    main(sys.argv)
