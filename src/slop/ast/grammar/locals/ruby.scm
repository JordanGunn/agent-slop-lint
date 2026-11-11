; Ruby names: receiver call methods and hash keys are not variable references.
(call method: (identifier) @ignore)
(pair key: (identifier) @ignore)

(class) @local.scope
(module) @local.scope
(method) @local.scope
(singleton_method) @local.scope
(lambda) @local.scope
(block) @local.scope
(do_block) @local.scope

(method_parameters (identifier) @local.definition.parameter)
(lambda_parameters (identifier) @local.definition.parameter)
(block_parameters (identifier) @local.definition.parameter)
(block_parameter (identifier) @local.definition.parameter)
(destructured_parameter (identifier) @local.definition.parameter)
(hash_splat_parameter (identifier) @local.definition.parameter)
(splat_parameter (identifier) @local.definition.parameter)
(keyword_parameter name: (identifier) @local.definition.parameter)
(optional_parameter name: (identifier) @local.definition.parameter)

(class body: (body_statement (method name: (identifier) @local.definition.method)))
(class body: (body_statement (singleton_method name: (identifier) @local.definition.method)))
(module body: (body_statement (method name: (identifier) @local.definition.method)))
(method name: (identifier) @local.definition.var)
(singleton_method name: (identifier) @local.definition.var)
(assignment left: (identifier) @local.definition.var)
(operator_assignment left: (identifier) @local.definition.var)
(left_assignment_list (identifier) @local.definition.var)
(rest_assignment (identifier) @local.definition.var)
(destructured_left_assignment (identifier) @local.definition.var)
(for pattern: (identifier) @local.definition.var)

(assignment left: (instance_variable) @local.definition.field)
(operator_assignment left: (instance_variable) @local.definition.field)
(instance_variable) @local.reference.member
(identifier) @local.reference
