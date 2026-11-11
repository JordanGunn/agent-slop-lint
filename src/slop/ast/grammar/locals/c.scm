; C scoping. Functions, blocks and for loops open scopes; a declaration binds its
; name in the innermost one, so a use before the declaration sees the outer name (bindings are
; ordered, hoisted_bindings is false).
;
; Declarators wrap the name (pointer, array, function pointer); each declaring context lists the
; wrappings up to three deep, plus the function-pointer shape. Deeper nesting is not bound.


; scopes
(function_definition) @local.scope
(field_declaration_list) @local.scope
(compound_statement) @local.scope
(for_statement) @local.scope
(preproc_function_def) @local.scope
; the parameter list of a prototype or function pointer: its names are not the enclosing scope's
(declaration declarator: (function_declarator parameters: (parameter_list) @local.scope))
(declaration declarator: (pointer_declarator declarator: (function_declarator parameters: (parameter_list) @local.scope)))
(declaration declarator: (parenthesized_declarator (pointer_declarator declarator: (function_declarator parameters: (parameter_list) @local.scope))))
(declaration declarator: (function_declarator declarator: (parenthesized_declarator (pointer_declarator declarator: (function_declarator parameters: (parameter_list) @local.scope)))))
(parameter_declaration declarator: (function_declarator parameters: (parameter_list) @local.scope))

; macro parameters
(preproc_params (identifier) @local.definition.parameter)

; parameters
(parameter_declaration declarator: [
   (identifier) @local.definition.parameter
   (_ declarator: (identifier) @local.definition.parameter)
   (parenthesized_declarator (identifier) @local.definition.parameter)
   (_ declarator: (_ declarator: (identifier) @local.definition.parameter))
   (parenthesized_declarator (_ declarator: (identifier) @local.definition.parameter))
   (_ declarator: (parenthesized_declarator (identifier) @local.definition.parameter))
   (parenthesized_declarator (parenthesized_declarator (identifier) @local.definition.parameter))
   (_ declarator: (_ declarator: (_ declarator: (identifier) @local.definition.parameter)))
   (parenthesized_declarator (_ declarator: (_ declarator: (identifier) @local.definition.parameter)))
   (_ declarator: (parenthesized_declarator (_ declarator: (identifier) @local.definition.parameter)))
   (parenthesized_declarator (parenthesized_declarator (_ declarator: (identifier) @local.definition.parameter)))
   (_ declarator: (_ declarator: (parenthesized_declarator (identifier) @local.definition.parameter)))
   (parenthesized_declarator (_ declarator: (parenthesized_declarator (identifier) @local.definition.parameter)))
   (_ declarator: (parenthesized_declarator (parenthesized_declarator (identifier) @local.definition.parameter)))
   (parenthesized_declarator (parenthesized_declarator (parenthesized_declarator (identifier) @local.definition.parameter)))
   (function_declarator declarator: (parenthesized_declarator (pointer_declarator declarator: (identifier) @local.definition.parameter)))
])
; struct and union members
(field_declaration declarator: [
   (field_identifier) @local.definition.field
   (_ declarator: (field_identifier) @local.definition.field)
   (parenthesized_declarator (field_identifier) @local.definition.field)
   (_ declarator: (_ declarator: (field_identifier) @local.definition.field))
   (parenthesized_declarator (_ declarator: (field_identifier) @local.definition.field))
   (_ declarator: (parenthesized_declarator (field_identifier) @local.definition.field))
   (parenthesized_declarator (parenthesized_declarator (field_identifier) @local.definition.field))
   (_ declarator: (_ declarator: (_ declarator: (field_identifier) @local.definition.field)))
   (parenthesized_declarator (_ declarator: (_ declarator: (field_identifier) @local.definition.field)))
   (_ declarator: (parenthesized_declarator (_ declarator: (field_identifier) @local.definition.field)))
   (parenthesized_declarator (parenthesized_declarator (_ declarator: (field_identifier) @local.definition.field)))
   (_ declarator: (_ declarator: (parenthesized_declarator (field_identifier) @local.definition.field)))
   (parenthesized_declarator (_ declarator: (parenthesized_declarator (field_identifier) @local.definition.field)))
   (_ declarator: (parenthesized_declarator (parenthesized_declarator (field_identifier) @local.definition.field)))
   (parenthesized_declarator (parenthesized_declarator (parenthesized_declarator (field_identifier) @local.definition.field)))
   (function_declarator declarator: (parenthesized_declarator (pointer_declarator declarator: (field_identifier) @local.definition.field)))
])

; names a scope binds
(declaration declarator: [
   (identifier) @local.definition.var
   (_ declarator: (identifier) @local.definition.var)
   (parenthesized_declarator (identifier) @local.definition.var)
   (_ declarator: (_ declarator: (identifier) @local.definition.var))
   (parenthesized_declarator (_ declarator: (identifier) @local.definition.var))
   (_ declarator: (parenthesized_declarator (identifier) @local.definition.var))
   (parenthesized_declarator (parenthesized_declarator (identifier) @local.definition.var))
   (_ declarator: (_ declarator: (_ declarator: (identifier) @local.definition.var)))
   (parenthesized_declarator (_ declarator: (_ declarator: (identifier) @local.definition.var)))
   (_ declarator: (parenthesized_declarator (_ declarator: (identifier) @local.definition.var)))
   (parenthesized_declarator (parenthesized_declarator (_ declarator: (identifier) @local.definition.var)))
   (_ declarator: (_ declarator: (parenthesized_declarator (identifier) @local.definition.var)))
   (parenthesized_declarator (_ declarator: (parenthesized_declarator (identifier) @local.definition.var)))
   (_ declarator: (parenthesized_declarator (parenthesized_declarator (identifier) @local.definition.var)))
   (parenthesized_declarator (parenthesized_declarator (parenthesized_declarator (identifier) @local.definition.var)))
   (function_declarator declarator: (parenthesized_declarator (pointer_declarator declarator: (identifier) @local.definition.var)))
])
(init_declarator declarator: [
   (identifier) @local.definition.var
   (_ declarator: (identifier) @local.definition.var)
   (parenthesized_declarator (identifier) @local.definition.var)
   (_ declarator: (_ declarator: (identifier) @local.definition.var))
   (parenthesized_declarator (_ declarator: (identifier) @local.definition.var))
   (_ declarator: (parenthesized_declarator (identifier) @local.definition.var))
   (parenthesized_declarator (parenthesized_declarator (identifier) @local.definition.var))
   (_ declarator: (_ declarator: (_ declarator: (identifier) @local.definition.var)))
   (parenthesized_declarator (_ declarator: (_ declarator: (identifier) @local.definition.var)))
   (_ declarator: (parenthesized_declarator (_ declarator: (identifier) @local.definition.var)))
   (parenthesized_declarator (parenthesized_declarator (_ declarator: (identifier) @local.definition.var)))
   (_ declarator: (_ declarator: (parenthesized_declarator (identifier) @local.definition.var)))
   (parenthesized_declarator (_ declarator: (parenthesized_declarator (identifier) @local.definition.var)))
   (_ declarator: (parenthesized_declarator (parenthesized_declarator (identifier) @local.definition.var)))
   (parenthesized_declarator (parenthesized_declarator (parenthesized_declarator (identifier) @local.definition.var)))
   (function_declarator declarator: (parenthesized_declarator (pointer_declarator declarator: (identifier) @local.definition.var)))
])
(function_definition declarator: (function_declarator declarator: (identifier) @local.definition.var))
(function_definition declarator: (pointer_declarator declarator: (function_declarator declarator: (identifier) @local.definition.var)))
(function_definition declarator: (function_declarator declarator: (parenthesized_declarator (pointer_declarator declarator: (function_declarator declarator: (identifier) @local.definition.var)))))
(enumerator name: (identifier) @local.definition.var)
(preproc_def name: (identifier) @local.definition.var)
(preproc_function_def name: (identifier) @local.definition.var)

(identifier) @local.reference
