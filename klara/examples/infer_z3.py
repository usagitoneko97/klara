import z3
import klara


class Z3Proxy(klara.InferProxy):
    def __init__(self, z3_expr):
        super(Z3Proxy, self).__init__(z3_expr)

    def __k_add__(self, other: klara.Const):
        """represent __add__ dunder method"""
        left = self.value
        right = other.value
        expr = left + right
        # we'll create a new Z3Proxy, wrapping the new expression
        return klara.inference.InferenceResult.load_result(Z3Proxy(expr))

    def __k_eq__(self, other: klara.Const):
        left = self.value
        right = other.value
        expr = left == right
        return klara.inference.InferenceResult.load_result(Z3Proxy(expr))

    def __k_bool__(self):
        yield klara.inference.InferenceResult(self, status=True)


AST2Z3TYPE_MAP = {"int": z3.Int, "float": z3.Real, "bool": z3.Bool, "str": z3.String}


@klara.inference.inference_transform_wrapper
def _infer_arg(node: klara.Arg, context):
    name = node.arg
    z3_var_type = AST2Z3TYPE_MAP[str(node.annotation)]
    z3_var = z3_var_type(name)
    proxy = Z3Proxy(z3_var)
    yield klara.inference.InferenceResult.load_result(proxy)


klara.MANAGER.register_transform(klara.Arg, _infer_arg)

source = """
    def foo(a: int):
        return a + 2 == 12
    """
tree = klara.parse(source)
for res in tree.body[0].infer_return_value():
    z3.solve(res.result.value)
