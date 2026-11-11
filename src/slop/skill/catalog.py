"""Every skill slop ships, by name. A new skill is a new function here and a manifest file."""
from __future__ import annotations

import json
from functools import partial
from pathlib import Path

from ..infer.bundle import prose
from ..infer.contract import schemas
from .model import Skill

_MANIFESTS = Path(__file__).parent / "manifests"


def _slop_infer() -> Skill:
    files = {"references/instructions.md": prose.instructions}
    for name in prose.references():
        files[f"references/{name}.md"] = partial(prose.reference, name)
    for document in schemas():
        files[f"assets/schemas/{document}.json"] = partial(_schema_text, document)
    return Skill(
        name="slop-infer",
        description=("Rule on slop linter warnings that need judgement: take the worklist from "
                     "`slop infer next`, judge each finding against its rubric, and return verdicts "
                     "with `slop infer apply`. Use when `slop lint` reports WARN findings, or when "
                     "asked to triage, clear or confirm them."),
        body=(_MANIFESTS / "slop-infer.md").read_text(encoding="utf-8"),
        files=files,
    )


def _schema_text(document: str) -> str:
    return json.dumps(schemas()[document], indent=2) + "\n"


SKILLS: dict[str, Skill] = {skill.name: skill for skill in (_slop_infer(),)}
