"""``slop lexicon``: a scope's vocabulary distribution, and its coverage by the project's vocabulary."""
from __future__ import annotations

import json
from pathlib import Path

from .. import ontology
from ..lexical import coverage
from . import resolve
from .render import add_output, header, label

#: below this many distinct words a Zipf fit says little
_MIN_DISTINCT = 15


def register(sub) -> None:
    p_lex = sub.add_parser("lexicon", help="print a scope's vocabulary distribution")
    resolve.add_root(p_lex)
    resolve.add_scope(p_lex, "qualname of a sub-scope (default: whole corpus)")
    p_lex.add_argument("--top", type=int, default=15, help="number of top tokens to show")
    p_lex.add_argument("--ontology", default=None,
                       help="a vocabulary file (default: the project's .slop/ontology.json, when it exists)")
    add_output(p_lex)
    p_lex.set_defaults(run=lambda a: view(a.root, a.output, scope=a.scope, top=a.top,
                                          scope_kind=a.scope_kind, ontology_file=a.ontology))


def view(root: str | Path, output: str = "human", *, scope: str | None = None, top: int = 15,
         scope_kind: str | None = None, ontology_file: str | Path | None = None) -> int:
    """Print the distribution of the words a scope declares: the Zipf fit and the head.

    With a vocabulary (``--ontology``, or the project's when it exists) it also reports how
    much of the declared names the vocabulary covers (see ``slop.lexical``)."""
    corpus = resolve.scan(root)
    if corpus is None:
        return 2
    target = resolve.target(corpus, scope, scope_kind)
    if target is None:
        return 2
    canonical = ontology.load(Path(ontology_file)) if ontology_file is not None else resolve.vocabulary(root)
    dist = target.lexicon().distribution(top=top)
    section, notes = _canonical(target, canonical, top)
    name = label(target, corpus)
    if output == "json":
        payload = {"scope": name, "kind": target.id.kind.value, **dist.as_dict()}
        if section is not None:
            payload["canonical"] = section
        print(json.dumps(payload, indent=2))
        return 0
    lines = [header("lexicon", f"{name} ({target.id.kind.value})", f"{dist.distinct} tokens · {dist.n} occ"),
             _statistics(dist),
             "  top: " + " ".join(f"{t}({c})" for t, c in dist.top) if dist.top else "  top: —"]
    print("\n".join(lines + notes))
    return 0


def _canonical(target, canonical: ontology.Scheme | None, top: int) -> tuple[dict | None, list[str]]:
    """The vocabulary's coverage of ``target``'s declared words, as JSON and as human lines. A
    vocabulary with no defined term yet (just drafted) covers nothing: that is said, not an error."""
    if canonical is None:
        return None, []
    if not canonical.defined():
        return ({"basis": "declared names", "vocabulary": canonical.name, "defined": 0},
                [f"  vocabulary {canonical.name}: no term has a definition yet, so it covers nothing"])
    cov = coverage(target.lexicon(), canonical)
    return {"basis": "declared names", **cov.as_dict(top=top)}, _coverage(cov, top)


def _statistics(dist) -> str:
    """The hapax ratio and the Zipf fit; with few words, a fit says little, and the line says so."""
    line = f"  hapax {dist.hapax_ratio:.2f} · Zipf α{dist.zipf_alpha:.2f} R²{dist.zipf_r2:.2f}"
    return line + " · small sample" if dist.distinct < _MIN_DISTINCT else line


def _coverage(cov, top: int) -> list[str]:
    """How much of the declared names the vocabulary covers, and the most used words it lacks."""
    pct = 100 * cov.occurrences_covered / cov.occurrences_total
    lines = [f"  vocabulary {cov.vocabulary}, over declared names: "
             f"{cov.occurrences_covered}/{cov.occurrences_total} occurrences ({pct:.0f}%) · "
             f"{len(cov.covered)}/{len(cov.covered) + len(cov.undefined)} tokens defined",
             f"  undefined (most used first, top {min(top, len(cov.undefined))} of {len(cov.undefined)}): "
             + (" ".join(f"{o.token}({o.count}×,{o.files}f)" for o in cov.undefined[:top]) or "—"),
             "  unused canonical: " + (" ".join(cov.unused) or "—")]
    if cov.unmeasurable:
        lines.append("  unmeasurable (stripped as noise): " + " ".join(cov.unmeasurable))
    return lines
