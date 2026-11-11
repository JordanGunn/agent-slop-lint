; Java scoping. Classes, methods, constructors, lambdas, blocks and the statements that bind
; (for, catch, try-with-resources, switch arms) open scopes. A member is visible throughout
; its class body (class_scope_visible is true), a local from its declaration on.

; not variable references
(field_access field: (identifier) @ignore)
(method_invocation object: (_) name: (identifier) @ignore)
(method_reference (_) . (identifier) @ignore)
(constructor_declaration name: (identifier) @ignore)
(compact_constructor_declaration name: (identifier) @ignore)
(scoped_identifier (identifier) @ignore)
(package_declaration (identifier) @ignore)
(import_declaration (identifier) @ignore)
(labeled_statement . (identifier) @ignore)
(break_statement (identifier) @ignore)
(continue_statement (identifier) @ignore)
(annotation name: (identifier) @ignore)
(marker_annotation name: (identifier) @ignore)
(element_value_pair key: (identifier) @ignore)
(record_pattern . (identifier) @ignore)

; scopes
(class_declaration) @local.scope
(interface_declaration) @local.scope
(record_declaration) @local.scope
(enum_declaration) @local.scope
(annotation_type_declaration) @local.scope
(object_creation_expression (class_body) @local.scope)
(method_declaration) @local.scope
(constructor_declaration) @local.scope
(compact_constructor_declaration) @local.scope
(lambda_expression) @local.scope
(block) @local.scope
(for_statement) @local.scope
(enhanced_for_statement) @local.scope
(catch_clause) @local.scope
(try_with_resources_statement) @local.scope
(switch_block_statement_group) @local.scope
(switch_rule) @local.scope

; record components are the record's fields
(record_declaration (formal_parameters (formal_parameter name: (identifier) @local.definition.field)))

; parameters
(formal_parameters (formal_parameter name: (identifier) @local.definition.parameter))
(formal_parameters (spread_parameter (variable_declarator name: (identifier) @local.definition.parameter)))
(catch_formal_parameter name: (identifier) @local.definition.parameter)
(lambda_expression parameters: (identifier) @local.definition.parameter)
(inferred_parameters (identifier) @local.definition.parameter)

; members
(field_declaration declarator: (variable_declarator name: (identifier) @local.definition.field))
(constant_declaration declarator: (variable_declarator name: (identifier) @local.definition.field))
(method_declaration name: (identifier) @local.definition.method)
(annotation_type_element_declaration name: (identifier) @local.definition.method)

; names a scope binds
(class_declaration name: (identifier) @local.definition.var)
(interface_declaration name: (identifier) @local.definition.var)
(record_declaration name: (identifier) @local.definition.var)
(enum_declaration name: (identifier) @local.definition.var)
(annotation_type_declaration name: (identifier) @local.definition.var)
(local_variable_declaration declarator: (variable_declarator name: (identifier) @local.definition.var))
(enhanced_for_statement name: (identifier) @local.definition.var)
(resource name: (identifier) @local.definition.var)
(type_pattern (identifier) @local.definition.var)
(instanceof_expression name: (identifier) @local.definition.var)
(record_pattern_component (identifier) @local.definition.var)

(identifier) @local.reference
