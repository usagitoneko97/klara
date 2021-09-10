import functools

import z3

from klara.core import inference, nodes, utilities, protocols
from klara.core.tree import infer_proxy
from klara.klara_z3 import cov_manager

MANAGER = cov_manager.CovManager()

DUNDER_TO_BIN_OP_METHOD = {
    "__add__": lambda a, b: a + b,
    "__sub__": lambda a, b: a - b,
    "__truediv__": lambda a, b: a / b,
    "__mod__": lambda a, b: a % b,
    "__and__": lambda a, b: a & b,
    "__or__": lambda a, b: a | b,
    "__floordiv__": lambda a, b: a // b,
    "__mul__": lambda a, b: a * b,
    "__pow__": lambda a, b: a ** b,
    "__xor__": lambda a, b: a ^ b,
    "__rshit__": lambda a, b: a >> b,
    "__lshift": lambda a, b: a << b,
}


def handle_z3_exceptions(f):
    def wrapper(*args, **kwargs):
        try:
            yield from f(*args, **kwargs)
        except z3.Z3Exception:
            yield inference.InferenceResult.load_result(nodes.Uninferable())

    return wrapper


class Z3Proxy(infer_proxy.InferProxy):
    def __init__(self, z3_var, default=None):
        """Initialize proxy with Z3 variable
        :param z3_expr: the z3 variable wrapped within the proxy
        :param default: default value if z3_var is not in the model
        """
        super(Z3Proxy, self).__init__(z3_var)
        self.defaults = {}
        if default is not None:
            self.defaults = {z3_var: default}
        self._setup_dunder()
        self._infer_unaryop = handle_z3_exceptions(self._infer_unaryop)
        self._infer_bool = handle_z3_exceptions(self._infer_bool)
        self._infer_builtins = handle_z3_exceptions(self._infer_builtins)

    def _default_op(
        self,
        op: str,
        other: inference.InferenceResult,
        method_name: str,
        context=None,
        self_result=inference.InferenceResult,
    ):
        try:
            yield from super(Z3Proxy, self)._default_op(op, other, method_name, context, self_result)
        except z3.Z3Exception:
            yield inference.InferenceResult.load_result(nodes.Uninferable(), inference_results=(other, self_result))

    def _infer(self, context=None, inferred_attr=None):
        if context and context.model is not None:
            try:
                z3_result = context.model.eval(self.value)
                defaults = []
                for arg in z3.z3util.get_vars(z3_result):
                    if arg in self.defaults:
                        defaults.append((arg, utilities.make_z3_const(self.defaults[arg])))
                    else:
                        MANAGER.logger.info("Z3", "Arg: {} from expr: {} is missing a default value", arg, z3_result)
                if defaults:
                    z3_result = z3.substitute(z3_result, defaults)
                z3_result = context.model.eval(z3_result, model_completion=True)
                py_val = utilities.get_py_val_from_z3_val(z3_result)
                if type(py_val) is not bool:
                    # don't add it in model used since bool value can't be change at later stage
                    context.z3_model_used[self.value] = z3_result
                yield inference.InferenceResult.load_result(nodes.Const(py_val))
            except NotImplementedError:
                yield inference.InferenceResult.load_result(self, substituted=True)
        else:
            yield inference.InferenceResult.load_result(self, substituted=True)

    @classmethod
    def init_expr(cls, z3_expr, defaults=None):
        c = cls(z3_var=z3_expr)
        c.defaults = defaults if defaults else {}
        return c

    def _setup_dunder(self) -> None:
        """setup all dunder method to do operation on proxy obj, and return an InferenceResult
        :return: None
        """
        for op, dunder in protocols.BIN_OP_DUNDER_METHOD.items():
            setattr(
                self,
                self._convert_dunder(dunder),
                functools.partial(self._binop_dunder_operation, op, protocols.BIN_OP_METHOD[op], False),
            )
        for op, reflected_dunder in protocols.REFLECTED_BIN_OP_DUNDER_METHOD.items():
            setattr(
                self,
                self._convert_dunder(reflected_dunder),
                functools.partial(self._binop_dunder_operation, op, protocols.BIN_OP_METHOD[op], True),
            )
        for compop, dunder in protocols.COMP_OP_DUNDER_METHOD.items():
            setattr(
                self,
                self._convert_dunder(dunder),
                functools.partial(self._compop_dunder_operation, protocols.COMP_METHOD[compop]),
            )
        for unary_op, dunder in protocols.UNARY_OP_DUNDER_METHOD.items():
            if dunder:
                setattr(
                    self,
                    self._convert_dunder(dunder),
                    functools.partial(self._unary_dunder_operation, protocols.UNARY_METHOD[unary_op]),
                )

    def _binop_dunder_operation(self, op: str, op_callback, reflected=False, other: nodes.Const = None):
        other_defaults = other.defaults if isinstance(other, Z3Proxy) else {}
        left = self.value
        right = utilities.make_z3_const(utilities.strip_constant_node(other))
        extras = []
        if op in ("&", ">>", "<<"):
            # cast left and right to BitVector for bit operation.
            left, right = z3.Int2BV(left, 64), z3.Int2BV(right, 64)
        elif op in ("/", "//"):
            # special handling divide, due to we have "//" operation in py2 protocol, and
            # it's incompatible with z3
            if op == "//":
                # convert result to floor.
                MANAGER.logger.warning(
                    "Z3", "Floor division (//) is not supported and will cast to (/), for node: {}", repr(self)
                )
            extras.append(right != 0)
            op_callback = lambda x, y: x / y

        elif op == "%":
            # casting left and right to int before doing modulo
            if not z3.is_int(left):
                left = z3.ToInt(left)
            if not z3.is_int(right):
                right = z3.ToInt(right)
            extras.append(right != 0)
        try:
            if not reflected:
                result = op_callback(left, right)
            else:
                result = op_callback(right, left)
            res = inference.InferenceResult(Z3Proxy.init_expr(result, {**self.defaults, **other_defaults}), status=True)
            res.z3_assumptions |= set(extras)
            return res
        except (z3.Z3Exception, TypeError):
            return inference.InferenceResult.load_result(nodes.Uninferable())

    def _compop_dunder_operation(self, op_callback, other: nodes.Const = None):
        other_defaults = other.defaults if isinstance(other, Z3Proxy) else {}
        try:
            other = utilities.make_z3_const(utilities.strip_constant_node(other))
            result = op_callback(self.value, other)
            return inference.InferenceResult(
                Z3Proxy.init_expr(result, {**self.defaults, **other_defaults}), status=True
            )
        except z3.Z3Exception:
            return inference.InferenceResult.load_result(nodes.Uninferable())

    def _unary_dunder_operation(self, op_callback):
        try:
            result = op_callback(self.value)
            return inference.InferenceResult(Z3Proxy.init_expr(result, {**self.defaults}), status=True)
        except z3.Z3Exception:
            return inference.InferenceResult.load_result(nodes.Uninferable())

    def __k_str__(self):
        try:
            if z3.is_string(self.value):
                val = self.value
            else:
                val = z3.IntToStr(self.value)
            return inference.InferenceResult.load_result(Z3Proxy.init_expr(val, {**self.defaults}))
        except (z3.Z3Exception, Exception):
            MANAGER.logger.warning("Can't convert expression of non integer: {} to string", self.value)
            return inference.InferenceResult.load_result(nodes.Uninferable())

    def __k_int__(self):
        try:
            return inference.InferenceResult.load_result(Z3Proxy.init_expr(z3.ToInt(self.value), {**self.defaults}))
        except z3.Z3Exception:
            return inference.InferenceResult.load_result(nodes.Uninferable())

    def __k_float__(self):
        try:
            return inference.InferenceResult.load_result(Z3Proxy.init_expr(z3.ToReal(self.value), {**self.defaults}))
        except z3.Z3Exception:
            return inference.InferenceResult.load_result(nodes.Uninferable())

    def __k_bool__(self):
        if z3.is_int(self.value) or z3.is_real(self.value) or z3.is_bv(self.value):
            yield inference.InferenceResult(Z3Proxy.init_expr(self.value != 0, self.defaults), status=True)
        elif z3.is_string(self.value):
            yield inference.InferenceResult(
                Z3Proxy.init_expr(self.value != z3.StringVal(""), self.defaults), status=True
            )
        else:
            yield inference.InferenceResult(self, status=True)

    def __k_not_bool__(self):
        for val in self.__k_bool__():
            yield inference.InferenceResult(
                Z3Proxy.init_expr(z3.Not(val.strip_inference_result()), self.defaults), status=True
            )
