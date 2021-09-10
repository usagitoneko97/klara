from .. import inference, manager, nodes
import ast

MANAGER = manager.AstManager()


class InferProxy(nodes.Const):
    # disable fields to avoid transform the `value` field of z3
    _fields = ()

    def __init__(self, value=None):
        super(InferProxy, self).__init__(value)
        self._infer_binop = self._default_op
        self._infer_comp_op = self._default_op
        self._hash = None

    def dunder_lookup(self, method):
        if method is not None:
            method = self._convert_dunder(method)
            return getattr(self, method)

    def _default_op(
        self,
        op: str,
        other: inference.InferenceResult,
        method_name: str,
        context=None,
        self_result=inference.InferenceResult,
    ):
        method = self.dunder_lookup(method_name)
        if method and other.status:
            res = method(other.result)
            res = res + other + self_result
            yield res
        else:
            MANAGER.logger.warning(
                "Z3", "Error in inferring of node: {}, op: {}, other: {}".format(self, op, other.result)
            )
            yield inference.InferenceResult.load_result(nodes.Uninferable(), inference_results=(other, self_result))

    def _infer_builtins(self, builtin: str, context):
        method = self.dunder_lookup("__" + builtin + "__")
        if method:
            yield method()
        else:
            MANAGER.logger.warning("Z3", "Builtin function {} not defined in class: {}", builtin, str(type(self)))
            yield inference.InferenceResult.load_result(nodes.Uninferable())

    def _infer_unaryop(self, op, method_name, context=None):
        def fail():
            MANAGER.logger.warning("Z3", "unary operation: {} failed on Z3 value: {}", op, self.value)

        method = self.dunder_lookup(method_name)
        if op == "not":
            method = self.dunder_lookup("__not_bool__")
            if method:
                yield from method()
            else:
                fail()
                yield inference.InferenceResult.load_result(nodes.Uninferable())
        else:
            if method:
                res = method()
                yield res
            else:
                fail()
                yield inference.InferenceResult.load_result(nodes.Uninferable())

    def _infer_bool(self, context=None):
        method = self.dunder_lookup("__bool__")
        if method:
            yield from method()
        else:
            MANAGER.logger.warning("Z3", "bool operation failed on Z3 value: {}", self.value)
            yield inference.InferenceResult.load_result(nodes.Uninferable())

    def to_ast(self) -> ast.AST:
        """
        Specify how to convert this node to ast expression, to be used as test case comparison
        :return: ast node
        """
        return super(InferProxy, self).to_ast()
        
    @staticmethod
    def _convert_dunder(dunder: str):
        """
        convert dunder method string to klara's specification
        :param dunder: dunder method in string, e.g. __str__
        :return: converted dunder
        """
        return "__k_" + dunder[2:]

    def __iter__(self):
        return self

    def __next__(self):
        raise StopIteration

    def _infer(self, context=None):
        yield inference.InferenceResult.load_result(self, substituted=True)

    def infer(self, context=None, inferred_attr=None):
        if not context or not context.model:
            yield inference.InferenceResult.load_result(self, substituted=True)
        else:
            yield from self._infer(context)

    def get_return_type(self):
        return type(None)

    def hash(self):
        return hash(self.value)

    def __hash__(self):
        if self._hash is not None:
            return self._hash
        self._hash = self.hash()
        return self._hash
