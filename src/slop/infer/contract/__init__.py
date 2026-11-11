"""The wire contract: the documents slop and an agent exchange, and their schemas."""
from __future__ import annotations

from .documents import DOCUMENTS, schemas
from .residue import Location, Question, Residue, RubricRef
from .ruling import Ruling
from .schema import ContractError, described, dump, parse, schema_of
from .verdict import Receipt, Rejection, Verdict, Verdicts
from .vocabulary import REASON_MAX_LENGTH, SCHEMA_VERSION, Outcome, Status

__all__ = [
    "DOCUMENTS", "REASON_MAX_LENGTH", "SCHEMA_VERSION", "ContractError", "Location", "Outcome", "Question",
    "Receipt", "Rejection", "Residue", "RubricRef", "Ruling", "Status", "Verdict", "Verdicts",
    "described", "dump", "parse", "schema_of", "schemas",
]
