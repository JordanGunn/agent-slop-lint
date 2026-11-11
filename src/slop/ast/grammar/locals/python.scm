; Python scoping. Functions, lambdas, comprehensions and class bodies open scopes; a method
; does not see its class body's names (class_scope_visible is false).

; the fields a class declares: class-level assignments and members assigned through self
(class_definition body: (block (expression_statement (assignment left: (identifier) @local.definition.field))))
(assignment left: (attribute object: (identifier) @_receiver attribute: (identifier) @local.definition.field)
  (#eq? @_receiver "self"))
(assignment left: (pattern_list (attribute object: (identifier) @_receiver attribute: (identifier) @local.definition.field))
  (#eq? @_receiver "self"))

; not variable references
(attribute attribute: (identifier) @ignore)
(keyword_argument name: (identifier) @ignore)

; scopes
(class_definition) @local.scope
(function_definition) @local.scope
(lambda) @local.scope
(list_comprehension) @local.scope
(set_comprehension) @local.scope
(dictionary_comprehension) @local.scope
(generator_expression) @local.scope

; parameters
(parameters (identifier) @local.definition.parameter)
(lambda_parameters (identifier) @local.definition.parameter)
(default_parameter name: (identifier) @local.definition.parameter)
(typed_parameter (identifier) @local.definition.parameter)
(typed_default_parameter name: (identifier) @local.definition.parameter)
(list_splat_pattern (identifier) @local.definition.parameter)
(dictionary_splat_pattern (identifier) @local.definition.parameter)

; names a scope binds
(function_definition name: (identifier) @local.definition.var)
(class_definition name: (identifier) @local.definition.var)
(assignment left: (identifier) @local.definition.var)
(assignment left: (pattern_list (identifier) @local.definition.var))
(assignment left: (tuple_pattern (identifier) @local.definition.var))
(augmented_assignment left: (identifier) @local.definition.var)
(for_statement left: (identifier) @local.definition.var)
(for_statement left: (pattern_list (identifier) @local.definition.var))
(for_statement left: (tuple_pattern (identifier) @local.definition.var))
(for_in_clause left: (identifier) @local.definition.var)
(for_in_clause left: (pattern_list (identifier) @local.definition.var))
(for_in_clause left: (tuple_pattern (identifier) @local.definition.var))
(as_pattern_target (identifier) @local.definition.var)
(named_expression name: (identifier) @local.definition.var)
(aliased_import alias: (identifier) @local.definition.import)
(import_statement name: (dotted_name . (identifier) @local.definition.import))
(import_from_statement name: (dotted_name (identifier) @local.definition.import))

(identifier) @local.reference
