; Go lexical scopes and names. Field identifiers are distinct from variable identifiers.
; Only a struct literal's identifier keys denote fields; map literal keys are expressions.
(composite_literal type: (type_identifier) body: (literal_value
  (keyed_element key: (literal_element (identifier) @ignore))))
(composite_literal type: (struct_type) body: (literal_value
  (keyed_element key: (literal_element (identifier) @ignore))))
((identifier) @ignore (#eq? @ignore "_"))

(struct_type) @local.scope
(function_declaration) @local.scope
(method_declaration) @local.scope
(func_literal) @local.scope
(block) @local.scope
(for_statement) @local.scope

(parameter_declaration name: (identifier) @local.definition.parameter)
(function_declaration name: (identifier) @local.definition.var)
(type_spec name: (type_identifier) @local.definition.var)
(short_var_declaration left: (expression_list (identifier) @local.definition.var))
(var_spec name: (identifier) @local.definition.var)
(range_clause left: (expression_list (identifier) @local.definition.var) ":=")

(field_declaration name: (field_identifier) @local.definition.field)

(identifier) @local.reference
