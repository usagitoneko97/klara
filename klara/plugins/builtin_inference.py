"""plugins inference for python builtins function"""
import builtins
import typing
from functools import partial

import math

from klara.core import exceptions, inference, manager, nodes, utilities

MANAGER = manager.AstManager()


def _builtin_filter_predicate(node: nodes.Call, builtin_name: str) -> bool:
    """based on assumption that builtin function call's `func` won't have links"""
    return isinstance(node.func, nodes.Name) and node.func.links is None and node.func.id == builtin_name


def register_builtin_transform(builtin_repr, builtin_infer_func):
    """Register inference transform function for builtin_name of python builtins functions
    This will register node.explicit_inference
    """
    MANAGER.register_transform(
        nodes.Call,
        inference.inference_transform_wrapper(builtin_infer_func),
        partial(_builtin_filter_predicate, builtin_name=builtin_repr),
    )


def _infer_single_arg(node, builtin_func_repr, context=None, inferred_attr=None):
    """infer all base class transforming call e.g. int(), str(), float()
    First, it must satisfy only 1 argument and no keyword argument condition.
    The call arg then is being inferred and will attempt to convert it by directly using builtin method.
    It will also look at dunder method defined if it's class instance.
    if the inferred has no value, it will look at the return type of the dunder method defined in builtins.pyi
    """
    if inferred_attr and "args" in inferred_attr:
        args = inferred_attr["args"]
    else:
        args = [a.infer(context) for a in node.args]
    builtin_func = getattr(builtins, builtin_func_repr)
    if len(args) > 1 or len(node.keywords) > 0:
        raise inference.UseInferenceDefault()
    elif len(args) == 0:
        yield from inference.const_factory(builtin_func())
        return
    arg = args[0]
    for val in arg:
        if val.status is False and val.result_type is not None:
            # only the type is known. Yield the return signature of the dunder method in builtins.pyi
            builtin_dunder_func_repr = "__" + builtin_func_repr + "__"
            dunder_method = val.result_type.dunder_lookup(builtin_dunder_func_repr)
            if context.config.is_type_inference() and dunder_method is not None:
                yield inference.InferenceResult.load_type(dunder_method.get_return_type())
                continue
        if val.status:
            infer_method = getattr(val.result, "_infer_builtins")
            for res in infer_method(builtin_func_repr, context):
                res += val
                yield res
        else:
            raise inference.UseInferenceDefault()


def _infer_round(node, context=None):
    """
    Interesting note in python 2 round function:
    round() will always return float. The way python 2 handles
    it is first called float(), which will triggers __float__,
    then perform rounding *without* delegating to __round__.
    __round__ is only available in python 3.

    The approach is here in dealing with type inference for
    python 2 is to just yield float type without getting the dunder method.
    """
    if MANAGER.config.py_version == 2:
        # Python 2's round() will always return float
        yield inference.InferenceResult.load_type(float)
        return
    round_func = _py2_round if MANAGER.config.py_version == 2 else round
    builtin_func_repr = "round"
    builtin_dunder_func_repr = "__" + builtin_func_repr + "__"
    if 0 > len(node.args) > 2 or len(node.keywords) > 0:
        raise inference.UseInferenceDefault()
    num_arg = node.args[0]
    try:
        ndigit_arg = node.args[1]
        ndigit_arg_iter = node.args[1].infer(context)
    except IndexError:
        ndigit_arg = None
        ndigit_arg_iter = [inference.InferenceResult.load_result(nodes.Const(0))]
    for number, ndigits in utilities.infer_product(num_arg.infer(context), ndigit_arg_iter):
        if number.status is False:
            # python 3's round() will delegate to __round__
            # only the type is known. Yield the return signature based on the input argument
            # since __round__ is overloaded in builtins.pyi
            if number.result_type is not None:
                dunder_method = number.result_type.dunder_lookup(builtin_dunder_func_repr)
                if context.config.is_type_inference() and dunder_method is not None:
                    if isinstance(dunder_method, nodes.OverloadedFunc):
                        for res in dunder_method.get_return_type(*node.args, context=context):
                            res += number + ndigits
                            yield res
                    else:
                        yield inference.InferenceResult.load_type(
                            dunder_method.get_return_type(), inference_results=(number, ndigits)
                        )
                        return
        try:
            if isinstance(number.result, nodes.Const):
                ndigits_value = None if ndigits.status is False else ndigits.result.value
                result = round_func(number.result.value, ndigits_value)
                for res in inference.const_factory(result):
                    res += number + ndigits
                    yield res
                continue
            elif isinstance(number.result, nodes.ClassInstance):
                # if it's a class instance, try to find __float__, map arg and infer the return value
                try:
                    dunder_method = number.result.dunder_lookup(builtin_dunder_func_repr)
                except exceptions.VariableNotExistStackError:
                    raise exceptions.DunderUnimplemented(builtin_dunder_func_repr, number.result.target_cls)
                else:
                    # map the argument in abs() to the target dunder method
                    context.map_args_to_func(number.result, ndigit_arg, func_node=dunder_method)
                    for res in dunder_method.infer_return_value(context):
                        res += number + ndigits
                        yield res
                continue

        except ValueError:
            raise inference.UseInferenceDefault()
            pass


def _infer_bool(node: nodes.Call, context=None, inferred_attr=None):
    if len(node.args) > 1 or len(node.keywords) > 0:
        raise inference.UseInferenceDefault()
    elif len(node.args) == 0:
        yield from inference.const_factory(bool())
        return
    arg = node.args[0]
    bool_arg = arg.wrap_bool()
    MANAGER.add_weak_ref(bool_arg)
    yield from bool_arg.infer(context)


def _py2_round(x: typing.Union[int, float], d: int = 0) -> float:
    d = d or 0
    p = 10 ** d
    if x > 0:
        return float(math.floor((x * p) + 0.5)) / p
    else:
        return float(math.ceil((x * p) - 0.5)) / p


def register():
    register_builtin_transform("abs", partial(_infer_single_arg, builtin_func_repr="abs"))
    register_builtin_transform("int", partial(_infer_single_arg, builtin_func_repr="int"))
    register_builtin_transform("float", partial(_infer_single_arg, builtin_func_repr="float"))
    register_builtin_transform("str", partial(_infer_single_arg, builtin_func_repr="str"))
    register_builtin_transform("len", partial(_infer_single_arg, builtin_func_repr="len"))
    register_builtin_transform("round", _infer_round)
    register_builtin_transform("bool", _infer_bool)
