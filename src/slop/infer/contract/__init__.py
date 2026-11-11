"""The wire contract: the documents slop and an agent exchange, and their schemas."""
from __future__ import annotations

from .documents import DOCUMENTS, schemas
from .residue import Excerpt, Question, Residue, RubricRef, Worklist
from .ruling import Ruling
from .schema import ContractError, described, dump, parse, schema_of
from .verdict import Receipt, Rejection, Verdict, Verdicts
from .vocabulary import REASON_MAX_LENGTH, SCHEMA_VERSION, Outcome

__all__ = [
    "DOCUMENTS", "REASON_MAX_LENGTH", "SCHEMA_VERSION", "ContractError", "Excerpt", "Outcome",
    "Question", "Receipt", "Rejection", "Residue", "RubricRef", "Ruling", "Verdict", "Verdicts",
    "Worklist", "described", "dump", "parse", "schema_of", "schemas",
]
