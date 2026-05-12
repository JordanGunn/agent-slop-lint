"""``Node`` — every tree-sitter node-type string referenced by v2 grammars.

``Node`` is a ``StrEnum`` so each member is interchangeable with its
string value: ``Node.IF_STATEMENT == "if_statement"``,
``frozenset({Node.IF_STATEMENT}) == frozenset({"if_statement"})``.
This lets walker code compare ``node.type`` (a raw string from
tree-sitter) against enum members without conversion.

Members are grouped by category in source order for readability. The
groupings are documentation-only; the enum itself is flat.

Note on field names: this enum covers tree-sitter NODE TYPE strings.
Tree-sitter ``field`` names (e.g. ``"body"``, ``"name"``,
``"declarator"``) live in a different namespace and are NOT part of
this enum. Operator-text strings (``"&&"``, ``"||"``, ``"and"``,
``"or"``) are source-code character sequences, not node types, and
are also NOT included.
"""
from __future__ import annotations

from enum import StrEnum


class Node(StrEnum):
    # ---- Identifier-family ------------------------------------------
    IDENTIFIER = "identifier"
    FIELD_IDENTIFIER = "field_identifier"
    PROPERTY_IDENTIFIER = "property_identifier"
    TYPE_IDENTIFIER = "type_identifier"
    QUALIFIED_IDENTIFIER = "qualified_identifier"
    OPERATOR = "operator"
    OPERATOR_NAME = "operator_name"
    DESTRUCTOR_NAME = "destructor_name"

    # ---- Callable definitions ---------------------------------------
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

    # ---- Class / struct / module / trait scopes ---------------------
    CLASS_DEFINITION = "class_definition"
    CLASS_DECLARATION = "class_declaration"
    CLASS_SPECIFIER = "class_specifier"
    STRUCT_DECLARATION = "struct_declaration"
    STRUCT_SPECIFIER = "struct_specifier"
    STRUCT_ITEM = "struct_item"
    INTERFACE_DECLARATION = "interface_declaration"
    RECORD_DECLARATION = "record_declaration"
    TRAIT_ITEM = "trait_item"
    IMPL_ITEM = "impl_item"
    TYPE_DECLARATION = "type_declaration"
    MODULE = "module"
    CLASS = "class"

    # ---- Wrapper / template -----------------------------------------
    TEMPLATE_DECLARATION = "template_declaration"
    SIGNATURE = "signature"
    CALL_EXPRESSION = "call_expression"

    # ---- C/C++ declarator chain ------------------------------------
    FUNCTION_DECLARATOR = "function_declarator"
    POINTER_DECLARATOR = "pointer_declarator"
    REFERENCE_DECLARATOR = "reference_declarator"
    PARENTHESIZED_DECLARATOR = "parenthesized_declarator"

    # ---- Decision / control-flow: conditionals ----------------------
    IF_STATEMENT = "if_statement"
    IF_EXPRESSION = "if_expression"
    IF = "if"
    ELIF_CLAUSE = "elif_clause"
    ELSEIF_CLAUSE = "elseif_clause"
    ELSIF = "elsif"
    IF_MODIFIER = "if_modifier"
    UNLESS_MODIFIER = "unless_modifier"

    # ---- Decision / control-flow: loops -----------------------------
    FOR_STATEMENT = "for_statement"
    FOR_EXPRESSION = "for_expression"
    FOR = "for"
    FOR_IN_STATEMENT = "for_in_statement"
    FOR_OF_STATEMENT = "for_of_statement"
    FOR_RANGE_LOOP = "for_range_loop"
    ENHANCED_FOR_STATEMENT = "enhanced_for_statement"
    FOREACH_STATEMENT = "foreach_statement"
    WHILE_STATEMENT = "while_statement"
    WHILE_EXPRESSION = "while_expression"
    WHILE = "while"
    WHILE_MODIFIER = "while_modifier"
    DO_STATEMENT = "do_statement"
    UNTIL = "until"
    UNTIL_MODIFIER = "until_modifier"

    # ---- Decision / control-flow: switch / match --------------------
    SWITCH_STATEMENT = "switch_statement"
    SWITCH_EXPRESSION = "switch_expression"
    SWITCH_CASE = "switch_case"
    SWITCH_LABEL = "switch_label"
    SWITCH_RULE = "switch_rule"
    SWITCH_SECTION = "switch_section"
    CASE_CLAUSE = "case_clause"
    CASE_STATEMENT = "case_statement"
    CASE = "case"
    WHEN = "when"
    MATCH_STATEMENT = "match_statement"
    MATCH_EXPRESSION = "match_expression"
    MATCH_ARM = "match_arm"
    EXPRESSION_SWITCH_STATEMENT = "expression_switch_statement"
    EXPRESSION_CASE = "expression_case"
    TYPE_SWITCH_STATEMENT = "type_switch_statement"
    TYPE_CASE = "type_case"
    SELECT_STATEMENT = "select_statement"
    COMMUNICATION_CASE = "communication_case"

    # ---- Decision / control-flow: try/catch -------------------------
    TRY_STATEMENT = "try_statement"
    CATCH_CLAUSE = "catch_clause"
    EXCEPT_CLAUSE = "except_clause"
    RESCUE = "rescue"
    RESCUE_MODIFIER = "rescue_modifier"
    BEGIN = "begin"

    # ---- Conditional / ternary expressions --------------------------
    CONDITIONAL_EXPRESSION = "conditional_expression"
    TERNARY_EXPRESSION = "ternary_expression"
    CONDITIONAL = "conditional"

    # ---- Boolean operators ------------------------------------------
    BOOLEAN_OPERATOR = "boolean_operator"
    BINARY_EXPRESSION = "binary_expression"
    BINARY = "binary"
