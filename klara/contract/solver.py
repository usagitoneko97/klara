import ast as ast_mod
from functools import partial
from typing import Union, List

import z3

from klara.core import recipe, nodes, utilities, inference
from klara.klara_z3 import cov_manager, inference_extension

MANAGER = cov_manager.CovManager()


class Assert:
    def __init__(self, module, funcdef, args, return_result: Union[nodes.Const, None] = None):
        self.funcdef = funcdef
        self.args = args
        self.return_result = return_result
        self.module = module

    def to_ast(self):
        call_func = ast_mod.Attribute(
            value=ast_mod.Name(id=self.module, ctx=ast_mod.Load()), attr=self.funcdef.name, ctx=ast_mod.Load()
        )
        call = ast_mod.Call(func=call_func, args=self.args, keywords=[])
        if self.return_result is None:
            ops = [ast_mod.IsNot()]
            comparators = [ast_mod.Constant(value=None)]
        elif isinstance(self.return_result, nodes.NameConstant):
            ops = [ast_mod.Is()]
            comparators = [ast_mod.Constant(value=self.return_result.value)]
        else:
            ops = [ast_mod.Eq()]
            comparators = [self.return_result.to_ast()]
        return ast_mod.Assert(test=ast_mod.Compare(left=call, ops=ops, comparators=comparators), msg=None)


class TestCase:
    def __init__(self, func, module, id=0):
        # list of all statements to initialize the function
        self.asserts = []
        self.func = func
        self.id = id
        self.module = module

    def to_ast(self):
        body = [ass.to_ast() for ass in self.asserts]
        test_func = ast_mod.FunctionDef(
            name=f"test_{self.func.name}_{self.id}",
            args=ast_mod.arguments(
                posonlyargs=[], args=[], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]
            ),
            body=body,
            decorator_list=[],
            returns=None,
        )
        return test_func


class TestModule:
    def __init__(self, module):
        self.functions = []
        self.module = module

    def to_ast(self):
        body = [ast_mod.Import([ast_mod.alias(self.module, None)])]
        body.extend([f.to_ast() for f in self.functions if f.asserts])
        return ast_mod.Module(body=body)


def _predicate(func_name, node):
    # FIXME: use infer to determine `require/ensure` from the correct module
    if isinstance(node, nodes.Call) and node.args and type(node.args[0]) is nodes.Lambda:
        if isinstance(node.func, nodes.Name):
            return str(node.func) == func_name
        elif isinstance(node.func, nodes.Attribute):
            return str(node.func.attr) == func_name
    return False


class ContractSolver(recipe.ClassInstanceBuilder):
    def __init__(self, cfg, as_tree, file_name):
        super(ContractSolver, self).__init__()
        self.cfg = cfg
        self.as_tree = as_tree
        self.file_name = file_name
        self.functions = []
        MANAGER.clear_infer_cache()
        MANAGER.load_cov_extensions()
        MANAGER.enable_infer_check_sat(inference_extension.infer_check_sat)
        self.cfg.apply_transform()
        self.id = 0

    def visit_functiondef(self, node):
        self.functions.append(node)

    def solve(self) -> TestModule:
        test_module = TestModule(self.file_name)
        self.visit(self.as_tree)
        for func in self.functions:
            MANAGER.logger.info("CONTRACT", "Analyzing function: {} at line: {}", func, getattr(func, "lineno", -1))
            try:
                ast_func = self.solve_function(func)
                test_module.functions.append(ast_func)
            except ValueError:
                MANAGER.logger.info(
                    "CONTRACT", "Skipped function: {} due to one of its argument doesn't have type", func
                )
            MANAGER.clear_z3_cache()
        return test_module

    def pre_conditions(self, func: nodes.FunctionDef) -> None:
        pre_conditions = []
        for decorator_func in filter(partial(_predicate, "require"), func.decorator_list):
            cond = decorator_func.args[0]
            try:
                new_args = self._parse_args(cond.args.args, func.args.args)
            except ValueError as e:
                MANAGER.logger.warning(
                    "CONTRACT",
                    "Arg: {} supply in lambda doesn't exist in function: {] at line: {} " ". Can't proceed",
                    e,
                    func,
                    func.lineno,
                )
                return None
            pre_conditions.extend(self._gather_conditions(new_args, cond))
        MANAGER.predicate_expr = z3.And(pre_conditions)

    def post_conditions(self, func, ret_val: inference.InferenceResult):
        post_conditions = []
        for decorator_func in filter(partial(_predicate, "ensure"), func.decorator_list):
            cond = decorator_func.args[0]
            try:
                new_args = self._parse_args(cond.args.args, func.args.args, {"result": ret_val.result})
            except ValueError as e:
                MANAGER.logger.warning(
                    "CONTRACT",
                    "Arg: {} supply in lambda doesn't exist in function: {] at line: {} " ". Can't proceed",
                    e,
                    func,
                    func.lineno,
                )
                return None
            post_conditions.extend(self._gather_conditions(new_args, cond))
        ret_val.z3_assumptions.add(z3.And(post_conditions))

    def solve_function(self, func: nodes.FunctionDef) -> TestCase:
        def log():
            MANAGER.logger.warning(
                "CONTRACT",
                "Failed to determine the return result for inferred node: {}. Using `is not None` test",
                ret_val,
            )

        with MANAGER.initialize_z3_var_from_func(func):
            self.context.no_cache = True
            self.pre_conditions(func)
            test_case = TestCase(func, self.id)
            for ret_val in func.infer_return_value(self.context):
                self.post_conditions(func, ret_val)
                for z3_result, _ in ret_val.check_sat(self.context):
                    if z3_result.sat:
                        if ret_val.status:
                            expanded_res = ret_val.expand(self.context, z3_result)
                            if expanded_res.status and isinstance(
                                expanded_res.result, (nodes.Const, nodes.NameConstant)
                            ):
                                returned_result = expanded_res.result
                            else:
                                log()
                                returned_result = None
                        else:
                            log()
                            returned_result = None
                        args = self.process_func_args(func, z3_result)
                        test_case.asserts.append(Assert(self.file_name, func, args, returned_result))
            self.id += 1
            self.context.no_cache = False
            return test_case

    def process_func_args(self, func: nodes.FunctionDef, z3_result) -> List[ast_mod.Constant]:
        """
        from a function arguments, query the args from the z3 model, and use `model.eval(model_completion=True)
        for argument not part of constraint.

        For argument that contain defaults, if it's in the model, the arg will have the model's value.
        If it's not in the model, the defaults will be used.
        """
        args = []

        def fail():
            MANAGER.logger.warning("CONTRACT", "Failed to determine the return result for argument: {}. ", arg)
            raise ValueError

        for arg in func.args.args:
            try:
                res = next(arg.infer(self.context))
                if res.status:
                    expanded_res = res.expand(self.context, z3_result)
                    if expanded_res.status and isinstance(expanded_res.result, (nodes.Const, nodes.NameConstant)):
                        returned_result = ast_mod.Constant(expanded_res.result.value)
                        args.append(returned_result)
                    else:
                        fail()
                else:
                    fail()
            except StopIteration:
                fail()
        return args

    def _parse_args(self, decorator_args, function_args, replace_map=None):
        """
        Return list of arg in function_args, order by decorator args.
        If decorator arg is in replace map, use the value of the map instead of the function
        :Raise: ValueError if arg in decorator doesn't exist in function
        """
        new_args = []
        for lambda_arg in decorator_args:
            # find lambda_arg in func
            if replace_map and str(lambda_arg) in replace_map:
                new_args.append(replace_map[str(lambda_arg)])
            else:
                found_arg = list(filter(lambda func: str(func) == str(lambda_arg), function_args))
                if not found_arg:
                    raise ValueError(lambda_arg)
                else:
                    new_args.append(found_arg[0])
        return new_args

    def _gather_conditions(self, args, decorator) -> list:
        """Call `decorator` with `args`, gather Prm nodes and convert to z3 expr"""
        self.context.map_args_to_func(*args, func_node=decorator)
        conditions = []
        for func_res in decorator.infer_return_value(self.context):
            if isinstance(func_res.result, nodes.Const):
                expr = utilities.strip_constant_node(func_res.result)
                conditions.append(expr)
        return conditions
