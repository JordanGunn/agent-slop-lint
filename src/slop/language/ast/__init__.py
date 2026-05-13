"""``slop.language.ast`` — tree-sitter node-type registries.

Ten semantic StrEnums, one per module:

  - ``Identifier``    — name-like nodes (identifier, field_identifier,
                        qualified_identifier, operator, destructor_name, …)
  - ``Callable``      — function/method/lambda/closure definitions
  - ``Scope``         — class/struct/module/trait/interface scopes
  - ``Wrapper``       — templates, signatures, declarator chains
  - ``Block``         — statement-sequence wrappers (block,
                        statement_block, compound_statement,
                        body_statement, switch_block, switch_body)
  - ``Conditional``   — if/elif/else + ternary
  - ``Loop``          — for/while/do/until variants
  - ``Switch``        — switch/match/select multi-way branching
  - ``Catch``         — try/catch/rescue/except (named Catch to avoid
                        shadowing Python's built-in Exception)
  - ``Operator``      — boolean/binary operator nodes (short-circuit
                        operator counting for complexity metrics)

Each enum subclasses ``StrEnum`` so its members are interchangeable
with their string values: ``Conditional.IF_STATEMENT == "if_statement"``,
``frozenset({Conditional.IF_STATEMENT}) == frozenset({"if_statement"})``.
Walker code compares ``node.type`` (a raw tree-sitter string) against
frozensets of enum members without conversion.

Out of scope: tree-sitter field names (``"body"``, ``"name"``,
``"declarator"``) live in a different namespace; operator-text strings
(``"&&"``, ``"||"``, ``"and"``, ``"or"``) are source-code character
sequences, not type names; punctuation tokens are syntactic. None of
those belong in these enums.
"""
from __future__ import annotations

from .block import Block
from .callable import Callable
from .catch import Catch
from .conditional import Conditional
from .identifier import Identifier
from .literal import Literal
from .loop import Loop
from .operator import Operator
from .scope import Scope
from .switch import Switch
from .wrapper import Wrapper

__all__ = [
    "Block",
    "Callable",
    "Catch",
    "Conditional",
    "Identifier",
    "Literal",
    "Loop",
    "Operator",
    "Scope",
    "Switch",
    "Wrapper",
]
