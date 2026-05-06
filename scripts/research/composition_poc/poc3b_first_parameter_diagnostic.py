"""PoC 3b: First-parameter clustering — diagnostic output framing.

Same algorithm as poc3, reformatted to name the diagnosis: the cluster
is a candidate for the receiver of a missing class. Includes an
honest false-positive caveat for clusters where the parameter is a
third-party library type (which would require a wrapper class).
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

DEF_RE = re.compile(r"^def\s+(\w+)\s*\(\s*([^,)]*)", re.MULTILINE)


def parse_first_param(raw):
    raw = raw.strip()
    if not raw or raw.startswith("*"):
        return (None, None)
    if ":" in raw:
        name, _, typ = raw.partition(":")
        return (name.strip(), typ.strip())
    return (raw, None)


def collect(paths):
    out = []
    for p in paths:
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in DEF_RE.finditer(text):
            fn = m.group(1)
            pname, ptype = parse_first_param(m.group(2) or "")
            if pname in (None, "self", "cls"):
                continue
            out.append((fn, p, pname, ptype))
    return out


# Heuristics for "wrapping this would be an anti-pattern"
THIRD_PARTY_HINTS = {"node", "tree"}  # tree-sitter types in slop's case
INFRASTRUCTURE_PARAMS = {"root", "file_path", "path"}  # legitimate scan-config params


def receiver_diagnosis(pname, types):
    """Return (verdict, advisory) for a candidate receiver.

    verdict: "strong" | "weak" | "false_positive"
    advisory: short prose
    """
    if pname in THIRD_PARTY_HINTS and not (types - {"Any", None, ""}):
        return ("false_positive",
                "This parameter is a third-party library type "
                "(e.g., tree-sitter AST node). Wrapping in a slop "
                "class would create an adapter layer with no clear "
                "benefit. Likely a coincidental cluster.")
    if pname in INFRASTRUCTURE_PARAMS:
        return ("weak",
                "This parameter is infrastructure (filesystem path / "
                "scan root) rather than a domain entity. The cluster "
                "reflects shared configuration plumbing, not a "
                "missing class.")
    return ("strong",
            f"`{pname}` is the natural receiver of these methods. "
            f"Each function's body operates on `{pname}` as its "
            f"primary subject. Folding them into a class with "
            f"`{pname}` as `self` is the textbook conversion.")


def report(items, min_cluster=3):
    by_name = defaultdict(list)
    for fn, path, pname, ptype in items:
        by_name[pname].append((fn, path, ptype))

    candidates = [(p, fns) for p, fns in by_name.items() if len(fns) >= min_cluster]
    candidates.sort(key=lambda x: -len(x[1]))

    lines = ["# composition.first_parameter_drift — missing-receiver candidates",
             ""]
    if not candidates:
        lines.append("_No first-parameter clusters of size >= 3._")
        return "\n".join(lines)

    for pname, fns in candidates:
        types = {t for _, _, t in fns if t}
        files = {path.name for _, path, _ in fns}
        verdict, advisory = receiver_diagnosis(pname, types)

        verdict_label = {
            "strong": "**Strong candidate** — likely missing class",
            "weak": "**Weak candidate** — infrastructure parameter",
            "false_positive": "**Likely false positive** — not a class candidate",
        }[verdict]

        lines.append(f"## Receiver candidate: `{pname}`  ({len(fns)} functions)")
        lines.append("")
        lines.append(f"{verdict_label}")
        lines.append("")
        lines.append(f"**Diagnosis**: {advisory}")
        lines.append("")
        if verdict == "strong":
            lines.append(f"**Compositional mechanism**: a class taking "
                         f"`{pname}` as `self`. Each of the {len(fns)} "
                         f"functions becomes a method. The current "
                         f"shape (`fn(self, args)`) becomes "
                         f"`self.fn(args)`.")
            lines.append("")
        lines.append(f"**Type annotations seen**: " +
                     (", ".join(f"`{t}`" for t in sorted(types)) if types
                      else "_(none — receiver is unannotated)_"))
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
