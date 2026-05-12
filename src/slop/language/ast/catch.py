"""``Catch`` — try/catch/rescue/except exception-handling node types.

Container forms (``try_statement``, Ruby ``begin``) and handler forms
(``catch_clause``, ``except_clause``, ``rescue``, ``rescue_modifier``).

Named ``Catch`` rather than ``Exception`` to avoid shadowing Python's
built-in ``Exception`` class — a file importing ``Exception`` from
this module would otherwise break local ``except Exception:`` clauses.
"""
from __future__ import annotations

from enum import StrEnum


class Catch(StrEnum):
    TRY_STATEMENT = "try_statement"
    CATCH_CLAUSE = "catch_clause"
    EXCEPT_CLAUSE = "except_clause"
    RESCUE = "rescue"
    RESCUE_MODIFIER = "rescue_modifier"
    BEGIN = "begin"
