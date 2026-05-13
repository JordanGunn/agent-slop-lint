"""``Block`` — tree-sitter node types that wrap a sequence of statements.

These are body-shape wrappers: ``block`` (Python, Go, Rust, Java, C#),
``statement_block`` (JS/TS), ``compound_statement`` (C/C++),
``body_statement`` (Ruby), plus the switch-body wrappers
(``switch_block`` / ``switch_block_statement_group`` in Java,
``switch_body`` in C#) that some grammars insert between a switch
container and its cases.

Used by ``Structure.combinatorial`` (NPath) to find the body of a
callable or branch and to descend through switch-body wrappers to
reach case nodes. Distinct from ``Wrapper`` — Wrapper wraps a NAME or
DEFINITION (template_declaration, signature, declarator chain), Block
wraps a STATEMENT SEQUENCE.
"""
from __future__ import annotations

from enum import StrEnum


class Block(StrEnum):
    BLOCK = "block"
    STATEMENT_BLOCK = "statement_block"
    COMPOUND_STATEMENT = "compound_statement"
    BODY_STATEMENT = "body_statement"
    SWITCH_BLOCK = "switch_block"
    SWITCH_BLOCK_STATEMENT_GROUP = "switch_block_statement_group"
    SWITCH_BODY = "switch_body"
