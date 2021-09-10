"""additional extension file to substitute all of the field defined in substitutes.
Substituted node is needed for 'flattening' a node with
respect to a particular node, because the usual `infer` will give us
`uninferable` result. This is useful in solving the
conditional equation with respect to the argument or any other node. e.g.
>>> context.node_ignore.add(nodes.Arg)
>>> def foo(x, y):
...     z = x + y
...     f = z * 2
...     if f == 2: pass   # `f` can be expressed as `(x + y) * 2`
Substitutes will only happens if following conditions are met
- `self` node is uninferable
- the mentioned field is inferable
A copy of `self` node will be created to replace the substituted field. This is
to avoid changing the node.
"""

import builtins

import z3

from klara.core import inference, nodes, utilities, decorators
from klara.klara_z3 import cov_manager
from klara.klara_z3.z3_nodes import Z3Proxy, handle_z3_exceptions

MANAGER = cov_manager.CovManager()


@inference.inference_transform_wrapper
def _infer_arg(node: nodes.Arg, context):
    # infer arg to get type information, and only replace result that only have type
    if MANAGER.arg_is_z3_var(node):
        for res in node._infer(context):
            default_value = res.result if res.status and res.result else None
            builtin_type = getattr(builtins, res.result_type.name) if res.result_type else None
            if builtin_type:
                proxy = Z3Proxy(
                    MANAGER.make_z3_var(node.arg, builtin_type), utilities.strip_constant_node(default_value)
                )
                yield inference.InferenceResult(proxy, status=True)
            else:
                yield res
    else:
        yield from node._infer(context)


@decorators.yield_at_least_once(lambda x: inference.InferenceResult.load_result(nodes.Uninferable(x)))
@handle_z3_exceptions
def _infer_bool_op_prm_field(node: nodes.BoolOp, context):
    """
    bool op will convert (a and b and c) to
    z3.If(bool(a), a, z3.If(bool(b), c))
    This assume that `a`, `b`, `c` must have the same sort.
    """
    for vals in utilities.infer_product(*(v.infer(context) for v in node.values)):
        if any(i.status and isinstance(i.result, Z3Proxy) for i in vals):
            defaults = {}
            z3_expr = None
            broke = False
            for val in reversed(vals):
                if val.status and isinstance(val.result, (nodes.Const, nodes.NameConstant)):
                    bool_node = val.result.wrap_bool() if node.op == "or" else val.result.invert_condition()
                    MANAGER.add_weak_ref(bool_node)
                    bool_val = next(bool_node.infer(context))
                    if z3_expr is None:
                        z3_expr = val.strip_inference_result()
                    else:
                        try:
                            z3_expr = z3.If(bool_val.strip_inference_result(), val.strip_inference_result(), z3_expr)
                        except z3.Z3Exception:
                            # sort miss match here, which is caused by python dynamic nature
                            broke = True
                            yield inference.InferenceResult.load_result(nodes.Uninferable(), inference_results=vals)
                            break
                else:
                    broke = True
                    break
                if isinstance(val.result, Z3Proxy):
                    defaults.update(val.result.defaults)
            if not broke:
                yield inference.InferenceResult(
                    Z3Proxy.init_expr(z3_expr, defaults), status=True, inference_results=vals
                )
        else:
            yield inference.UseDefaultInferenceOnce({"values": vals})


_infer_bool_op_prm_field_inference = inference.inference_transform_wrapper(_infer_bool_op_prm_field)


def flatten_arg_predicate(node: nodes.Arg):
    """
    Construct expression in relative to the argument of any function/method.
    Only target argument that is not `self`
    :return:
    """
    return str(node) != "self"


def register():
    MANAGER.register_transform(nodes.Arg, _infer_arg)
    MANAGER.register_transform(nodes.BoolOp, _infer_bool_op_prm_field_inference)


def unregister():
    MANAGER.unregister_transform(nodes.Arg, _infer_arg)
    MANAGER.unregister_transform(nodes.BoolOp, _infer_bool_op_prm_field_inference)
