"""PoC 3: First-parameter clustering for "methods on a missing class".

Algorithm
---------
1. For each top-level function, extract the first parameter:
   - name (e.g., ``node``, ``content``, ``config``)
   - type annotation if present
2. Group functions by first-param name.
3. Flag groups of size >= 3: these functions all operate on the same
   thing and are likely methods on a missing class.

Theoretical basis
-----------------
- Object-oriented analysis: functions sharing a first argument are
  the textbook signature of methods on a class. The receiver in
  ``foo.method(args)`` becomes ``method(foo, args)`` once you remove
  the class.
- Refactoring research: "Move Method" / "Convert Procedural Design
  to Objects" (Fowler, *Refactoring*) — explicitly identifies the
  shared-first-parameter pattern as the canonical class-conversion
  trigger.

Usage
-----
    python poc3_first_parameter_drift.py FILE [FILE ...]
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

# Match: def NAME ( first_param[: TYPE]?  ...
DEF_RE = re.compile(
    r"^def\s+(\w+)\s*\(\s*([^,)]*)",
    re.MULTILINE,
)


def parse_first_param(raw: str) -> tuple[str | None, str | None]:
    """Return (param_name, type_annotation) from the raw first-param text.

    Raw forms we handle:
        ``node``                   → ("node", None)
        ``node: Any``              → ("node", "Any")
        ``content: bytes``         → ("content", "bytes")
        ``self``                   → ("self", None)   — filtered out
        ``cls``                    → ("cls", None)    — filtered out
        ``*args``                  → (None, None)
        ``**kwargs``               → (None, None)
    """
    raw = raw.strip()
    if not raw or raw.startswith("*"):
        return (None, None)
    if ":" in raw:
        name, _, typ = raw.partition(":")
        return (name.strip(), typ.strip())
    return (raw, None)


def collect(paths):
    """Return [(fn_name, path, first_param_name, first_param_type), ...]."""
    out = []
    for p in paths:
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in DEF_RE.finditer(text):
            fn = m.group(1)
            raw_param = m.group(2) or ""
            pname, ptype = parse_first_param(raw_param)
            if pname in (None, "self", "cls"):
                continue
            out.append((fn, p, pname, ptype))
    return out


def report(items, min_cluster: int = 3) -> str:
    by_name: dict[str, list[tuple[str, Path, str | None]]] = defaultdict(list)
    for fn, path, pname, ptype in items:
        by_name[pname].append((fn, path, ptype))

    candidates = [(p, fns) for p, fns in by_name.items() if len(fns) >= min_cluster]
    candidates.sort(key=lambda x: -len(x[1]))

    lines = ["# PoC 3 — First-parameter drift candidates\n"]
    if not candidates:
        lines.append("_No first-parameter clusters of size >= 3._\n")
        return "\n".join(lines)

    for pname, fns in candidates:
        types = {t for _, _, t in fns if t is not None}
        files = {path.name for _, path, _ in fns}
        lines.append(f"## First parameter: `{pname}`  ({len(fns)} functions)\n")
        if types:
            lines.append(f"**Type annotations seen**: " + ", ".join(f"`{t}`" for t in sorted(types)))
        lines.append(f"**Files**: " + ", ".join(sorted(files)))
        lines.append("")
        lines.append("| Function | File | First param type |")
        lines.append("|---|---|---|")
        for fn, path, ptype in sorted(fns, key=lambda x: (x[1].name, x[0])):
            ann = ptype if ptype else "_(unannotated)_"
            lines.append(f"| `{fn}` | {path.name} | {ann} |")
        lines.append("")
    return "\n".join(lines)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        sys.exit(1)
    paths = [Path(p) for p in argv[1:]]
    items = collect(paths)
    print(report(items, min_cluster=3))


if __name__ == "__main__":
    main(sys.argv)
