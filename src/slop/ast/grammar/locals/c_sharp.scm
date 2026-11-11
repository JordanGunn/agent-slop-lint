; C# scoping. Types, methods, constructors, local functions, lambdas, blocks and the statements
; that bind (for, foreach, catch, using, switch sections and arms, queries) open scopes. A
; member is visible throughout its type body (class_scope_visible is true), a local from its
; declaration on.

; not variable references: member names, labels, named arguments, namespaces
(member_access_expression name: (identifier) @ignore)
(member_binding_expression name: (identifier) @ignore)
(constructor_declaration name: (identifier) @ignore)
(argument name: (identifier) @ignore)
(labeled_statement . (identifier) @ignore)
(goto_statement (identifier) @ignore)
(qualified_name (identifier) @ignore)
(alias_qualified_name (identifier) @ignore)
(using_directive (identifier) @ignore)
(namespace_declaration name: (identifier) @ignore)
(file_scoped_namespace_declaration name: (identifier) @ignore)
(attribute name: (identifier) @ignore)
(generic_name (identifier) @ignore)

; identifiers in type positions
(base_list (identifier) @ignore)
(variable_declaration type: (identifier) @ignore)
(parameter type: (identifier) @ignore)
(property_declaration type: (identifier) @ignore)
(method_declaration returns: (identifier) @ignore)
(local_function_statement type: (identifier) @ignore)
(catch_declaration type: (identifier) @ignore)
(declaration_pattern type: (identifier) @ignore)
(declaration_expression type: (identifier) @ignore)
(object_creation_expression type: (identifier) @ignore)
(cast_expression type: (identifier) @ignore)
(array_type type: (identifier) @ignore)
(nullable_type (identifier) @ignore)

; scopes
(class_declaration) @local.scope
(interface_declaration) @local.scope
(struct_declaration) @local.scope
(record_declaration) @local.scope
(enum_declaration) @local.scope
(method_declaration) @local.scope
(constructor_declaration) @local.scope
(local_function_statement) @local.scope
(lambda_expression) @local.scope
(anonymous_method_expression) @local.scope
(block) @local.scope
(for_statement) @local.scope
(foreach_statement) @local.scope
(catch_clause) @local.scope
(using_statement) @local.scope
(switch_section) @local.scope
(switch_expression_arm) @local.scope
(query_expression) @local.scope

; a primary constructor's parameters are members of the type
(class_declaration (parameter_list (parameter name: (identifier) @local.definition.field)))
(struct_declaration (parameter_list (parameter name: (identifier) @local.definition.field)))
(record_declaration (parameter_list (parameter name: (identifier) @local.definition.field)))

; parameters
(parameter name: (identifier) @local.definition.parameter)
(implicit_parameter) @local.definition.parameter
(catch_declaration name: (identifier) @local.definition.parameter)

; members
(field_declaration (variable_declaration (variable_declarator . (identifier) @local.definition.field)))
(event_field_declaration (variable_declaration (variable_declarator . (identifier) @local.definition.field)))
(property_declaration name: (identifier) @local.definition.field)
(method_declaration name: (identifier) @local.definition.method)

; names a scope binds
(class_declaration name: (identifier) @local.definition.var)
(interface_declaration name: (identifier) @local.definition.var)
(struct_declaration name: (identifier) @local.definition.var)
(record_declaration name: (identifier) @local.definition.var)
(enum_declaration name: (identifier) @local.definition.var)
(local_function_statement name: (identifier) @local.definition.var)
(variable_declarator . (identifier) @local.definition.var)
(foreach_statement left: (identifier) @local.definition.var)
(foreach_statement left: (tuple_pattern (identifier) @local.definition.var))
(declaration_pattern name: (identifier) @local.definition.var)
(declaration_expression name: (identifier) @local.definition.var)
(from_clause name: (identifier) @local.definition.var)
(let_clause . (identifier) @local.definition.var)
(join_clause . (identifier) @local.definition.var)
(var_pattern (identifier) @local.definition.var)

(identifier) @local.reference
