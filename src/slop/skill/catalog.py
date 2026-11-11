"""Every skill slop ships, by name. Slop ships one, `slop`: the single point of agentic access.
A skill is a function here and a manifest in ``manifests/``."""
from __future__ import annotations

import json
from functools import partial
from pathlib import Path

from ..infer.bundle import prose
from ..infer.contract import schemas
from .model import Skill

_MANIFESTS = Path(__file__).parent / "manifests"


def _slop() -> Skill:
    files = {"references/infer.md": prose.instructions}
    for name in prose.references():
        files[f"references/{name}.md"] = partial(prose.reference, name)
    for document in schemas():
        files[f"assets/schemas/{document}.json"] = partial(_schema_text, document)
    return Skill(
        name="slop",
        description=("Run the slop linter and code-structure tool from a plain-language ask: lint "
                     "code, explain violations, find where names are defined, show a codebase's "
                     "structure, dependencies and hotspots, and judge slop's WARN findings with "
                     "`slop infer`. Use whenever the user mentions slop, linting, code quality or "
                     "code structure."),
        body=(_MANIFESTS / "slop.md").read_text(encoding="utf-8"),
        files=files,
    )


def _schema_text(document: str) -> str:
    return json.dumps(schemas()[document], indent=2) + "\n"


SKILLS: dict[str, Skill] = {skill.name: skill for skill in (_slop(),)}
