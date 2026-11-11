; JavaScript scoping. Functions, arrows, methods, classes, blocks, loops and catch clauses open
; scopes; every binding is hoisted (hoisted_bindings) and a method does not see its class
; body's names. Destructuring patterns are followed two levels deep in declarations and one in parameters,
; loops and catch clauses.

; not variable references
(import_specifier name: (identifier) @ignore alias: (identifier))
(export_specifier alias: (identifier) @ignore)
(jsx_opening_element name: (identifier) @ignore (#match? @ignore "^[a-z]"))
(jsx_closing_element name: (identifier) @ignore (#match? @ignore "^[a-z]"))
(jsx_self_closing_element name: (identifier) @ignore (#match? @ignore "^[a-z]"))

; class fields: declared in the body, or assigned through this anywhere (an update, +=, declares nothing)
(field_definition property: (property_identifier) @local.definition.field)
(field_definition property: (private_property_identifier) @local.definition.field)
(assignment_expression left: (member_expression object: (this) property: [(property_identifier) (private_property_identifier)] @local.definition.field))


; scopes
(function_declaration) @local.scope
(generator_function_declaration) @local.scope
(function_expression) @local.scope
(generator_function) @local.scope
(arrow_function) @local.scope
(method_definition) @local.scope
(class_declaration) @local.scope
(class) @local.scope
(class_static_block) @local.scope
(statement_block) @local.scope
(switch_body) @local.scope
(for_statement) @local.scope
(for_in_statement) @local.scope
(catch_clause) @local.scope

; parameters
(formal_parameters [(identifier) @local.definition.parameter (array_pattern [(identifier) @local.definition.parameter (assignment_pattern left: (identifier) @local.definition.parameter) (rest_pattern (identifier) @local.definition.parameter)]) (object_pattern [(shorthand_property_identifier_pattern) @local.definition.parameter
    (object_assignment_pattern left: (shorthand_property_identifier_pattern) @local.definition.parameter)
    (pair_pattern value: [(identifier) @local.definition.parameter (assignment_pattern left: (identifier) @local.definition.parameter)])
    (rest_pattern (identifier) @local.definition.parameter)])])
(formal_parameters (assignment_pattern left: [(identifier) @local.definition.parameter (array_pattern [(identifier) @local.definition.parameter (assignment_pattern left: (identifier) @local.definition.parameter) (rest_pattern (identifier) @local.definition.parameter)]) (object_pattern [(shorthand_property_identifier_pattern) @local.definition.parameter
    (object_assignment_pattern left: (shorthand_property_identifier_pattern) @local.definition.parameter)
    (pair_pattern value: [(identifier) @local.definition.parameter (assignment_pattern left: (identifier) @local.definition.parameter)])
    (rest_pattern (identifier) @local.definition.parameter)])]))
(formal_parameters (rest_pattern [(identifier) @local.definition.parameter (array_pattern [(identifier) @local.definition.parameter (assignment_pattern left: (identifier) @local.definition.parameter) (rest_pattern (identifier) @local.definition.parameter)]) (object_pattern [(shorthand_property_identifier_pattern) @local.definition.parameter
    (object_assignment_pattern left: (shorthand_property_identifier_pattern) @local.definition.parameter)
    (pair_pattern value: [(identifier) @local.definition.parameter (assignment_pattern left: (identifier) @local.definition.parameter)])
    (rest_pattern (identifier) @local.definition.parameter)])]))

(arrow_function parameter: (identifier) @local.definition.parameter)

; names a scope binds

(function_declaration name: (identifier) @local.definition.var)

(generator_function_declaration name: (identifier) @local.definition.var)

(function_expression name: (identifier) @local.definition.var)

(generator_function name: (identifier) @local.definition.var)

(class_declaration name: (identifier) @local.definition.var)

; variables
(variable_declarator name: [(identifier) @local.definition.var (array_pattern [(identifier) @local.definition.var (array_pattern [(identifier) @local.definition.var (assignment_pattern left: (identifier) @local.definition.var) (rest_pattern (identifier) @local.definition.var)]) (object_pattern [(shorthand_property_identifier_pattern) @local.definition.var
    (object_assignment_pattern left: (shorthand_property_identifier_pattern) @local.definition.var)
    (pair_pattern value: [(identifier) @local.definition.var (assignment_pattern left: (identifier) @local.definition.var)])
    (rest_pattern (identifier) @local.definition.var)]) (assignment_pattern left: [(identifier) @local.definition.var (array_pattern [(identifier) @local.definition.var (assignment_pattern left: (identifier) @local.definition.var) (rest_pattern (identifier) @local.definition.var)]) (object_pattern [(shorthand_property_identifier_pattern) @local.definition.var
    (object_assignment_pattern left: (shorthand_property_identifier_pattern) @local.definition.var)
    (pair_pattern value: [(identifier) @local.definition.var (assignment_pattern left: (identifier) @local.definition.var)])
    (rest_pattern (identifier) @local.definition.var)])]) (rest_pattern [(identifier) @local.definition.var (array_pattern [(identifier) @local.definition.var (assignment_pattern left: (identifier) @local.definition.var) (rest_pattern (identifier) @local.definition.var)]) (object_pattern [(shorthand_property_identifier_pattern) @local.definition.var
    (object_assignment_pattern left: (shorthand_property_identifier_pattern) @local.definition.var)
    (pair_pattern value: [(identifier) @local.definition.var (assignment_pattern left: (identifier) @local.definition.var)])
    (rest_pattern (identifier) @local.definition.var)])])]) (object_pattern [(shorthand_property_identifier_pattern) @local.definition.var
    (object_assignment_pattern left: (shorthand_property_identifier_pattern) @local.definition.var)
    (pair_pattern value: [(identifier) @local.definition.var (array_pattern [(identifier) @local.definition.var (assignment_pattern left: (identifier) @local.definition.var) (rest_pattern (identifier) @local.definition.var)]) (object_pattern [(shorthand_property_identifier_pattern) @local.definition.var
    (object_assignment_pattern left: (shorthand_property_identifier_pattern) @local.definition.var)
    (pair_pattern value: [(identifier) @local.definition.var (assignment_pattern left: (identifier) @local.definition.var)])
    (rest_pattern (identifier) @local.definition.var)]) (assignment_pattern left: [(identifier) @local.definition.var (array_pattern [(identifier) @local.definition.var (assignment_pattern left: (identifier) @local.definition.var) (rest_pattern (identifier) @local.definition.var)]) (object_pattern [(shorthand_property_identifier_pattern) @local.definition.var
    (object_assignment_pattern left: (shorthand_property_identifier_pattern) @local.definition.var)
    (pair_pattern value: [(identifier) @local.definition.var (assignment_pattern left: (identifier) @local.definition.var)])
    (rest_pattern (identifier) @local.definition.var)])])])
    (rest_pattern [(identifier) @local.definition.var (array_pattern [(identifier) @local.definition.var (assignment_pattern left: (identifier) @local.definition.var) (rest_pattern (identifier) @local.definition.var)]) (object_pattern [(shorthand_property_identifier_pattern) @local.definition.var
    (object_assignment_pattern left: (shorthand_property_identifier_pattern) @local.definition.var)
    (pair_pattern value: [(identifier) @local.definition.var (assignment_pattern left: (identifier) @local.definition.var)])
    (rest_pattern (identifier) @local.definition.var)])])])])

; loop variables
(for_in_statement kind: _ left: [(identifier) @local.definition.var (array_pattern [(identifier) @local.definition.var (assignment_pattern left: (identifier) @local.definition.var) (rest_pattern (identifier) @local.definition.var)]) (object_pattern [(shorthand_property_identifier_pattern) @local.definition.var
    (object_assignment_pattern left: (shorthand_property_identifier_pattern) @local.definition.var)
    (pair_pattern value: [(identifier) @local.definition.var (assignment_pattern left: (identifier) @local.definition.var)])
    (rest_pattern (identifier) @local.definition.var)])])

; catch
(catch_clause parameter: [(identifier) @local.definition.var (array_pattern [(identifier) @local.definition.var (assignment_pattern left: (identifier) @local.definition.var) (rest_pattern (identifier) @local.definition.var)]) (object_pattern [(shorthand_property_identifier_pattern) @local.definition.var
    (object_assignment_pattern left: (shorthand_property_identifier_pattern) @local.definition.var)
    (pair_pattern value: [(identifier) @local.definition.var (assignment_pattern left: (identifier) @local.definition.var)])
    (rest_pattern (identifier) @local.definition.var)])])

(import_specifier !alias name: (identifier) @local.definition.import)
(import_specifier alias: (identifier) @local.definition.import)
(import_clause (identifier) @local.definition.import)
(namespace_import (identifier) @local.definition.import)

(identifier) @local.reference
(shorthand_property_identifier) @local.reference
