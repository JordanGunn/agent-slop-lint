"""The documents of the exchange, and the schema of each. `slop infer schema` prints these.

``residue`` is the object `slop lint --output json` attaches to a finding; ``verdicts`` is what
the agent sends to `slop infer apply`; ``receipt`` is what it answers."""
from __future__ import annotations

from typing import Any

from .residue import Residue
from .schema import schema_of
from .verdict import Receipt, Verdicts

#: Name of each document and the type that declares it.
DOCUMENTS: dict[str, type] = {"residue": Residue, "verdicts": Verdicts, "receipt": Receipt}


def schemas() -> dict[str, dict[str, Any]]:
    """The JSON Schema of every document, by name."""
    return {name: schema_of(cls) for name, cls in DOCUMENTS.items()}
