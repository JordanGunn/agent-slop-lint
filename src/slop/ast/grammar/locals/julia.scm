; Julia function bodies are lexical scopes; structs contain fields, not bare-name members.
; Function names remain free: the signature nests the name beneath the function scope, so
; defining it here would misclassify recursive calls as locals. Short-form g(a) = ... is
; likewise not modeled as a function scope and its parameters remain free.
(field_expression _ (identifier) @ignore)
(typed_expression _ (identifier) @ignore)
(struct_definition (typed_expression . (identifier) @local.definition.field))
(struct_definition (identifier) @local.definition.field)

(struct_definition) @local.scope
(function_definition) @local.scope
(arrow_function_expression) @local.scope
(do_clause) @local.scope
(let_statement) @local.scope
(for_statement) @local.scope

(function_definition (signature (call_expression (argument_list (identifier) @local.definition.parameter))))
(function_definition (signature (call_expression (argument_list (named_argument (identifier) @local.definition.parameter)))))
(function_definition (signature (call_expression (argument_list (typed_expression . (identifier) @local.definition.parameter)))))
(arrow_function_expression (argument_list (identifier) @local.definition.parameter))
(arrow_function_expression (identifier) @local.definition.parameter)
(do_clause (argument_list (identifier) @local.definition.parameter))
(for_binding . (identifier) @local.definition.var)
(for_binding . (tuple_expression (identifier) @local.definition.var))
(let_statement (identifier) @local.definition.var)
(let_binding . (identifier) @local.definition.var)
(assignment . (identifier) @local.definition.var)
(identifier) @local.reference
