; Rust block-local names and pattern bindings. Field/type names are separate node types.
; Tuple-struct pattern heads name constructors, not local variables.
; Known limit: for-pattern bindings also appear visible in their own iterator expression.
; Known limit: if-let bindings also appear visible in the else branch.
(tuple_struct_pattern type: (identifier) @ignore)
((identifier) @ignore (#eq? @ignore "_"))

(struct_item) @local.scope
(function_item) @local.scope
(closure_expression) @local.scope
(block) @local.scope
(for_expression) @local.scope
(match_arm) @local.scope
(if_expression) @local.scope

(parameter pattern: (identifier) @local.definition.parameter)
(parameter pattern: (tuple_pattern (identifier) @local.definition.parameter))
(parameter pattern: (tuple_struct_pattern (identifier) @local.definition.parameter))
(parameter pattern: (struct_pattern (field_pattern pattern: (identifier) @local.definition.parameter)))
(parameter pattern: (struct_pattern (field_pattern name: (shorthand_field_identifier) @local.definition.parameter)))
(function_item name: (identifier) @local.definition.var)
(let_declaration pattern: (identifier) @local.definition.var value: (_)? @local.definition-value)
(let_declaration pattern: (tuple_pattern (identifier) @local.definition.var) value: (_)? @local.definition-value)
(let_declaration pattern: (tuple_struct_pattern (identifier) @local.definition.var) value: (_)? @local.definition-value)
(let_declaration pattern: (struct_pattern (field_pattern pattern: (identifier) @local.definition.var)) value: (_)? @local.definition-value)
(let_declaration pattern: (struct_pattern (field_pattern name: (shorthand_field_identifier) @local.definition.var)) value: (_)? @local.definition-value)
(for_expression pattern: (identifier) @local.definition.var value: (_)? @local.definition-value)
(for_expression pattern: (tuple_pattern (identifier) @local.definition.var) value: (_)? @local.definition-value)
(for_expression pattern: (tuple_struct_pattern (identifier) @local.definition.var) value: (_)? @local.definition-value)
(match_pattern (identifier) @local.definition.var)
(match_pattern (tuple_pattern (identifier) @local.definition.var))
(match_pattern (tuple_struct_pattern (identifier) @local.definition.var))
(let_condition pattern: (identifier) @local.definition.var)
(let_condition pattern: (tuple_struct_pattern (identifier) @local.definition.var))
(let_condition pattern: (tuple_pattern (identifier) @local.definition.var))
(let_condition pattern: (struct_pattern (field_pattern pattern: (identifier) @local.definition.var)))
(let_condition pattern: (struct_pattern (field_pattern name: (shorthand_field_identifier) @local.definition.var)))

(field_declaration name: (field_identifier) @local.definition.field)

(identifier) @local.reference
(shorthand_field_identifier) @local.reference
