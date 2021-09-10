"""
extension to support math.ceil and math.floor
floor and ceil by default will just bypassed.
Specifically target ceil division (math.ceil(float(x)/y))
"""
from klara.core import inference, nodes
from klara.klara_z3 import cov_manager
from klara.plugins import builtin_inference

MANAGER = cov_manager.CovManager()


@inference.inference_transform_wrapper
def _infer_math_ceil_floor(node: nodes.Call, context):
    """The strategy will be ignoring the call"""
    MANAGER.logger.warning("COV", "Ignoring {} call at line: {}", node.func, node.lineno)
    yield from node.args[0].infer(context)


@inference.inference_transform_wrapper
def _infer_ceil_division(node: nodes.Call, context):
    """
    Ceiling division will be implemented by using (x + y - 1) / y
    taken from: https://stackoverflow.com/a/2745086/9677833
    """
    left = node.args[0].args[0].left.args[0]
    right = node.args[0].args[0].right
    x_p_y = nodes.BinOp()
    x_p_y.postinit(left, "+", right)
    x_p_y_min_1 = nodes.BinOp()
    x_p_y.parent = x_p_y_min_1
    x_p_y_min_1.postinit(x_p_y, "-", nodes.Const(1))
    x_p_y_min_1_div_y = nodes.BinOp()
    x_p_y_min_1.parent = x_p_y_min_1_div_y
    x_p_y_min_1_div_y.postinit(x_p_y_min_1, "/", right)
    MANAGER.apply_transform(x_p_y_min_1_div_y)
    yield from x_p_y_min_1_div_y.infer(context)


def _is_math_ceil_floor(node: nodes.Call, math_or_ceil=None):
    fields = math_or_ceil or ("ceil", "floor")
    return (
        hasattr(node.func, "links")
        and node.func.links is None
        and isinstance(node.func, nodes.Attribute)
        and str(node.func.attr) in fields
        and str(node.func.value) == "math"
        and len(node.args) > 0
    )


def _is_ceil_div(node: nodes.Call):
    return (
        builtin_inference._builtin_filter_predicate(node, "int")
        and len(node.args) > 0
        and isinstance(node.args[0], nodes.Call)
        and _is_math_ceil_floor(node.args[0], ("ceil",))
        and len(node.args[0].args) > 0
        and isinstance(node.args[0].args[0], nodes.BinOp)
        and isinstance(node.args[0].args[0].left, nodes.Call)
        and builtin_inference._builtin_filter_predicate(node.args[0].args[0].left, "float")
        and len(node.args[0].args[0].left.args) > 0
        and isinstance(node.args[0].args[0].right, nodes.Const)
    )


def register():
    MANAGER.register_transform(nodes.Call, _infer_math_ceil_floor, _is_math_ceil_floor)
    MANAGER.register_transform(nodes.Call, _infer_ceil_division, _is_ceil_div)


def unregister():
    MANAGER.unregister_transform(nodes.Call, _infer_math_ceil_floor, _is_math_ceil_floor)
    MANAGER.unregister_transform(nodes.Call, _infer_ceil_division, _is_ceil_div)
