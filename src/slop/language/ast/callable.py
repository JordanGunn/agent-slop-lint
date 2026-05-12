"""``Callable`` — tree-sitter node types that define new callable scopes.

Function definitions, method definitions, lambdas, closures, and
language-specific anonymous-block forms (Ruby ``do_block``/``block``,
Julia ``do_clause``). Anything a grammar's ``callable()`` classmethod
would return belongs here.

Note: ``slop.tree.records`` also exports a ``Callable`` dataclass
(the record type for a callable's parsed metadata). Files using both
will alias one of them at import time.
"""
from __future__ import annotations

from enum import StrEnum


class Callable(StrEnum):
    # Function definitions
    FUNCTION_DEFINITION = "function_definition"
    ASYNC_FUNCTION_DEFINITION = "async_function_definition"
    FUNCTION_DECLARATION = "function_declaration"
    FUNCTION_EXPRESSION = "function_expression"
    FUNCTION_ITEM = "function_item"
    GENERATOR_FUNCTION_DECLARATION = "generator_function_declaration"
    LOCAL_FUNCTION_STATEMENT = "local_function_statement"
    # Method definitions
    METHOD = "method"
    METHOD_DECLARATION = "method_declaration"
    METHOD_DEFINITION = "method_definition"
    SINGLETON_METHOD = "singleton_method"
    CONSTRUCTOR_DECLARATION = "constructor_declaration"
    # Anonymous / closure callables
    LAMBDA = "lambda"
    LAMBDA_EXPRESSION = "lambda_expression"
    ARROW_FUNCTION = "arrow_function"
    ARROW_FUNCTION_EXPRESSION = "arrow_function_expression"
    CLOSURE_EXPRESSION = "closure_expression"
    FUNC_LITERAL = "func_literal"
    DO_BLOCK = "do_block"
    DO_CLAUSE = "do_clause"
    BLOCK = "block"
