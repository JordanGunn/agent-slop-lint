"""A skill as the Agent Skills specification defines it (agentskills.io/specification)."""
from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath

MANIFEST = "SKILL.md"

#: The specification's limits on the frontmatter fields slop writes.
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")      # lowercase, digits, single hyphens inside


@dataclass(frozen=True)
class Skill:
    """A skill: what the frontmatter says, the manifest body, and its other files.

    ``files`` maps a path relative to the skill's directory to the function that produces the
    file's text, so the text is read from its source when the skill is built."""

    name: str
    description: str
    body: str
    files: Mapping[str, Callable[[], str]]

    def __post_init__(self) -> None:
        if len(self.name) > MAX_NAME_LENGTH or not _NAME.match(self.name):
            raise ValueError(f"skill name {self.name!r}: 1-{MAX_NAME_LENGTH} lowercase letters, "
                             "digits and single hyphens, not at either end")
        if not 0 < len(self.description) <= MAX_DESCRIPTION_LENGTH:
            raise ValueError(f"skill {self.name}: description must be 1-{MAX_DESCRIPTION_LENGTH} characters")
        for path in self.files:
            parts = PurePosixPath(path).parts
            if PurePosixPath(path).is_absolute() or ".." in parts or path == MANIFEST:
                raise ValueError(f"skill {self.name}: file path {path!r} must stay inside the skill")

    def manifest(self) -> str:
        """The ``SKILL.md`` text: YAML frontmatter, then the body."""
        # A JSON string is a valid YAML double-quoted scalar, so the description needs no escaping rules of its own.
        return f"---\nname: {self.name}\ndescription: {json.dumps(self.description)}\n---\n\n{self.body}"

    def tree(self) -> dict[str, str]:
        """Every file of the skill, by path relative to its directory, manifest first."""
        return {MANIFEST: self.manifest(), **{path: text() for path, text in sorted(self.files.items())}}
