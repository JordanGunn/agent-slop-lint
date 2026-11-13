"""Every skill slop ships, by name. Slop ships one, `slop`: the single point of agentic access.
A skill is a function here and a manifest in ``manifests/``."""
from __future__ import annotations

from pathlib import Path

from .model import Skill

_MANIFESTS = Path(__file__).parent / "manifests"


def _slop() -> Skill:
    return Skill(
        name="slop",
        description=("Run the slop linter and code-structure tool from a plain-language ask: lint "
                     "code, explain violations, find where names are defined, show a codebase's "
                     "structure, dependencies and hotspots, and curate the project's vocabulary. "
                     "Use whenever the user mentions slop, linting, code quality or "
                     "code structure."),
        body=(_MANIFESTS / "slop.md").read_text(encoding="utf-8"),
        files={},
    )


SKILLS: dict[str, Skill] = {skill.name: skill for skill in (_slop(),)}
