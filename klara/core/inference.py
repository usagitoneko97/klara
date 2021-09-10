import builtins
import contextlib
import copy
import enum
import functools
import itertools
from typing import Union

import z3

from . import context_mod, decorators, exceptions, manager, nodes, utilities
from .node_classes import BUILT_IN_TYPE
from .protocols import (
    BIN_OP_DUNDER_METHOD,
    BIN_OP_METHOD,
    COMP_METHOD,
    COMP_OP_DUNDER_METHOD,
    REFLECTED_BIN_OP_DUNDER_METHOD,
    UNARY_METHOD,
    UNARY_OP_DUNDER_METHOD,
    COMP_REFLECTED_OP,
)

MANAGER = manager.AstManager()


class InferenceResult(object):
    """Object for every result to `node.infer()`"""

    __slots__ = (
        "result",
        "result_type",
        "status",
        "bound_instance",
        "_bound_conditions",
        "infer_path",
        "_selected_operand",
        "_z3_assumptions",
        "_hash_only_result",
        "_hash",
        "abutments",
        "inverted_conditions",
    )

    def __init__(
        self,
        result=None,
        result_type=None,
        status=False,
        bound_instance=None,
        bound_conditions=None,
        infer_path=None,
        selected_operand=None,
        inference_results=None,
        abutments=None,
    ):
        self.result = result
        self.result_type = result_type
        # True -> inferred successfully
        self.status = status
        self.bound_instance = bound_instance
        self.infer_path = infer_path or []
        # conditions attach to the statement of inferring
        self._bound_conditions = set()
        self._selected_operand = {}
        self._z3_assumptions = set()
        # flag to determine what field to hash. Set it to True to hash only the result.
        self._hash_only_result = False
        self._hash = None
        self.abutments = abutments or set()
        self.init(bound_conditions, selected_operand, inference_results)
        # keep track of which conditions is inverted, so that in evaluate the bound conditions path,
        # the condition might evaluated to the pre-inverted conditions that is suppose to be inverted,
        # but not, and will result in unsat
        self.inverted_conditions = set()

    @property
    def hash_only_result(self):
        return self._hash_only_result

    @hash_only_result.setter
    def hash_only_result(self, value):
        self._hash = None
        self._hash_only_result = value

    @property
    def z3_assumptions(self):
        return self._z3_assumptions

    @z3_assumptions.setter
    def z3_assumptions(self, value):
        self._hash = None
        self._z3_assumptions = value

    @property
    def bound_conditions(self):
        return self._bound_conditions

    @bound_conditions.setter
    def bound_conditions(self, value):
        self._hash = None
        self._bound_conditions = value

    @property
    def selected_operand(self):
        return self._selected_operand

    @selected_operand.setter
    def selected_operand(self, value):
        self._hash = None
        self._selected_operand = value

    def init(self, bound_conditions=None, selected_operand=None, inference_results=None, inverted_conds=None):
        if bound_conditions:
            self.bound_conditions |= bound_conditions
        if selected_operand:
            self.selected_operand.update(selected_operand)
        if inference_results:
            self.merge_other_results(inference_results)
        if inverted_conds:
            self.inverted_conditions |= inverted_conds

    def merge_other_results(self, inference_results):
        for result in inference_results:
            self.bound_conditions |= result.bound_conditions
            self.z3_assumptions |= result.z3_assumptions
            self.selected_operand.update(result.selected_operand)
            self.abutments |= result.abutments
            self.hash_only_result |= result.hash_only_result

    def __repr__(self):
        return repr(self.result)

    def __hash__(self):
        if self._hash is None:
            if self.hash_only_result:
                self._hash = hash(self.result)
            else:
                self._hash = hash(
                    tuple(self.bound_conditions) + (self.result, self.result_type) + tuple(self.z3_assumptions)
                )
        return self._hash

    @property
    def real_conditions(self):
        result = []
        for assumption in self.z3_assumptions:
            result.append(list(filter(lambda x: x[1] == assumption, MANAGER.z3_assumptions_cache.items()))[0])
        return result

    @classmethod
    def load_result(
        cls,
        result,
        bound_instance=None,
        substituted=False,
        bound_conditions=None,
        selected_operand=None,
        inference_results=None,
        hash_only_result=False,
        abutments=None,
        inverted_conds=None,
    ):
        c = cls()
        c.result = result
        c.status = True
        c.bound_conditions = set()
        c.selected_operand = {}
        c.hash_only_result = hash_only_result
        if abutments:
            c.abutments |= abutments
        c.init(bound_conditions, selected_operand, inference_results, inverted_conds)
        try:
            if isinstance(result, (nodes.Const, nodes.NameConstant)):
                if result.value.__class__ in MANAGER.builtins_ast_cls:
                    c.result_type = MANAGER.builtins_ast_cls[result.value.__class__]
            elif isinstance(result, nodes.BaseContainer):
                c.result_type = MANAGER.builtins_ast_cls[result.get_actual_type()]
            elif isinstance(result, nodes.Uninferable):
                c.status = False
            elif substituted:
                c.status = 2
            c.bound_instance = bound_instance
            r_bound = result.get_bound_conditions()
            c.bound_conditions |= r_bound
        except AttributeError:
            pass
        return c

    @classmethod
    def load_type(
        cls,
        result_type: builtins = type(None),
        overwrite_type=None,
        inference_results=None,
        hash_only_result=False,
        abutments=None,
    ):
        c = cls()
        c.bound_conditions = set()
        c.selected_operand = {}
        c.result_type = overwrite_type if overwrite_type else MANAGER.builtins_ast_cls[result_type]
        c.result = "<type({})>".format(c.result_type)
        c.init(inference_results=inference_results)
        c.hash_only_result = hash_only_result
        if abutments:
            c.abutments |= abutments
        return c

    @classmethod
    def from_other(
        cls, other, bound_conditions=None, selected_operand=None, inference_results=None, inverted_conditions=None
    ):
        c = cls()
        c.selected_operand = copy.copy(other.selected_operand)
        if selected_operand:
            c.selected_operand.update(selected_operand)
        c.infer_path = other.infer_path
        c.result = other.result
        c.result_type = other.result_type
        c.status = other.status
        c.bound_instance = other.bound_instance
        c.bound_conditions = copy.copy(other.bound_conditions)
        c.z3_assumptions |= other.z3_assumptions
        c.hash_only_result = other.hash_only_result
        c.abutments |= other.abutments
        c.init(bound_conditions, selected_operand, inference_results, inverted_conditions)
        return c

    def __add__(self, other):
        """merge some properties from other Inference result"""
        if other:
            self.bound_conditions |= other.bound_conditions
            self.selected_operand.update(other.selected_operand)
            self.z3_assumptions |= other.z3_assumptions
            self.hash_only_result |= other.hash_only_result
            self.abutments |= other.abutments
        return self

    def __radd__(self, other):
        return self.__add__(other)

    def add_infer_path(self, node):
        if not self.infer_path and (self.status or self.result_type):
            self.infer_path = [node]

    def strip_inference_result(self):
        """Strip the const/instance out of the result."""
        return utilities.strip_constant_node(self.result)


class MultiInferenceResult(InferenceResult):
    """Merging of multiple inference result into one"""

    def __init__(self, *args, **kwargs):
        super(MultiInferenceResult, self).__init__(*args, **kwargs)

    def combine_selected_operand(self, results):
        for res in results:
            for k, v in res.selected_operand.items():
                if k in self.selected_operand:
                    if type(self.selected_operand[k]) is set:
                        if type(v) is set:
                            self.selected_operand[k] |= v
                        else:
                            self.selected_operand[k].add(v)
                    else:
                        val = self.selected_operand[k]
                        if type(v) is set:
                            self.selected_operand[k] = v | {val}
                        else:
                            self.selected_operand[k] = {v, val}
                else:
                    self.selected_operand[k] = v

    @classmethod
    def combine_inference_results(cls, results):
        z3_assumptions = set()
        if len(results) == 1:
            return results[0]
        for val in results:
            if len(val.z3_assumptions) == 1:
                z3_assumptions.add(list(val.z3_assumptions)[0])
            elif len(val.z3_assumptions) > 1:
                z3_assumptions.add(z3.And(val.z3_assumptions))
        res = cls.from_other(results[0], inference_results=results)
        if len(z3_assumptions) > 0:
            z3_or = z3.Or(z3_assumptions)
            res.z3_assumptions = {z3_or}
            res.selected_operand.clear()
        res.combine_selected_operand(results)
        return res


def convert_to_inferred(inferred):
    for k, v in inferred.items():
        if isinstance(v, (tuple, list)):
            inferred[k] = ((vi,) for vi in v)
        else:
            inferred[k] = (v,)
    return inferred


class UseDefaultInferenceOnce:
    def __init__(self, inferred, bound_conditions=None):
        # convert the value to iterator
        self.bound_conditions = bound_conditions
        self.inferred = convert_to_inferred(inferred)


class UseInferenceDefault(Exception):
    pass


class UseInferredAttr(Exception):
    def __init__(self, **kwargs):
        self.inferred_attr = kwargs


def cache_yield_different(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """when hash() return True, it will not be combined"""
        _cache = {}
        results = list(func(*args, **kwargs))
        for res in results:
            _cache.setdefault(hash(res), []).append(res)
        for _, value in _cache.items():
            if len(value) > 1:
                yield MultiInferenceResult.combine_inference_results(value)
            else:
                yield value[0]

    return wrapper


@decorators.lru_cache_context
@cache_yield_different
@decorators.inference_path
@MANAGER.infer_wrapper
def infer(self, context=context_mod.context_ins, inferred_attr=None):
    """inference entry point"""
    inference_count = 0
    inferred_attr = {} if inferred_attr is None else inferred_attr
    has_next = True
    expl = None
    if self.explicit_inference is not None:
        expl = self.explicit_inference(self, context=context)
    while has_next:
        has_next = False
        try:
            if expl is not None:
                res = next(expl)
                if isinstance(res, UseDefaultInferenceOnce):
                    inferred_attr = res.inferred
                    has_next = True
                else:
                    has_next = True
                    yield res
                    continue
        except UseInferenceDefault:
            pass
        except UseInferredAttr as e:
            inferred_attr = e.inferred_attr
        except StopIteration:
            return

        yield from self._infer(context, inferred_attr)


def base_infer(self, context=context_mod.context_ins, inferred_attr=None):
    """using use_def chain info to infer the value"""
    if not hasattr(self, "links"):
        yield InferenceResult.load_result(nodes.Uninferable(self))


nodes.BaseNode._infer = base_infer
nodes.BaseNode.infer = infer


def infer_end(self, context=context_mod.context_ins, inferred_attr=None):
    yield InferenceResult.load_result(self)


def infer_function_def(self, context=context_mod.context_ins, inferred_attr=None):
    if self.is_property():
        yield from self.infer_return_value(context)
        return
    wrapped_decorator = [InferenceResult.load_result(self, context.bound_instance)]
    if self not in context.decorator_ignore:
        for dec_name in reversed(self.decorator_list):
            try:
                dec = next(dec_name.infer(context))
            except StopIteration:
                continue
            if dec.status is True:
                for func in wrapped_decorator:
                    func = func.result
                    if not isinstance(dec.result, nodes.FunctionDef):
                        MANAGER.logger.warning(
                            "INFER",
                            "Decorator: {} in function: {} line: {} is not a FunctionDef",
                            dec.result,
                            self,
                            self.lineno,
                        )
                        continue
                    else:
                        context.map_args_to_func(func, func_node=dec.result)
                    context.decorator_ignore.add(func)
                    wrapped_decorator[:] = []
                    wrapped_decorator.extend(list(dec.result.infer_return_value(context)))
        yield from wrapped_decorator
        return
    yield from wrapped_decorator


def infer_return_value(self, context=context_mod.context_ins, inferred_attr=None):
    if self.refer_to_block is None:
        # FIXME: quick hack for any typestub file not being Cfg'd
        try:
            yield InferenceResult.load_type(self.get_return_type())
        except exceptions.UnannotatedError:
            yield InferenceResult.load_result(nodes.Uninferable(None, override_msg="node is unannotated"))
    else:
        for tail in self.refer_to_block.func_tail:
            val = tail.ssa_code.code_list[-1].value
            if val:
                yield from val.infer(context=context)


def infer_lambda_return_value(self, context=context_mod.context_ins, inferred_attr=None):
    yield from self.body.infer(context)


nodes.Const._infer = infer_end
nodes.NameConstant._infer = infer_end
nodes.FunctionDef._infer = infer_function_def
nodes.Lambda._infer = infer_end
nodes.FunctionDef.infer_return_value = infer_return_value
nodes.Lambda.infer_return_value = infer_lambda_return_value
nodes.ClassDef._infer = infer_end
nodes.ClassInstance._infer = infer_end
nodes.LocalsDictNode._infer = infer_end


def extract_const(self, context=None):
    if context is None:
        context = context_mod.InferenceContext()
    old_conditions_mode = context.conditions_mode
    # disable conditions inferring
    context.conditions_mode = context_mod.ConditionsMode.DISABLE
    yield from self._extract_const(context)
    context.conditions_mode = old_conditions_mode


nodes.BaseNode.extract_const = extract_const


def extract_const_base(self, context=None):
    for res in self.infer(context):
        yield res


def extract_const_end(self, context=context_mod.context_ins):
    yield InferenceResult.load_result(self)


def extract_const_sequence(self, context=None, ctype=list):
    for vals in utilities.infer_product(*(v.extract_const(context) for v in self.elts)):
        # get the conditions and strip the Inference Result
        try:
            yield InferenceResult.load_result(reverse_container_factory(ctype(vals)), inference_results=vals)
        except exceptions.ContainerExtractError:
            yield InferenceResult.load_result(nodes.Uninferable(), inference_results=vals)


def extract_const_const(self, context=None):
    yield InferenceResult.load_result(self.value)


def extract_const_dict(self, context=None):
    # no reason to yield a constant version of dict, since it
    # can't be used with any bin op method
    yield from ()


nodes.ClassInstance._extract_const = extract_const_end
nodes.BaseNode._extract_const = extract_const_base
nodes.List._extract_const = functools.partialmethod(extract_const_sequence, ctype=list)
nodes.Set._extract_const = functools.partialmethod(extract_const_sequence, ctype=set)
nodes.Tuple._extract_const = functools.partialmethod(extract_const_sequence, ctype=tuple)
nodes.Dict._extract_const = extract_const_dict


def _infer_unaryop(op: str, val: InferenceResult, context=None):
    if isinstance(val, nodes.Uninferable):
        yield InferenceResult.load_result(
            nodes.Uninferable(override_msg="unary op failed with op: {} value: {}".format(op, val))
        )
    else:
        try:
            dunder_repr = UNARY_OP_DUNDER_METHOD[op]
            infer_method = getattr(val.result, "_infer_unaryop")
            yield from infer_method(op, dunder_repr, context=context)
        except (exceptions.VariableNotExistStackError, AttributeError):
            # Dunder method is unimplemented
            yield InferenceResult.load_result(
                nodes.Uninferable(override_msg="Dunder method {} is unimplemented in instance: {}".format(op, val))
            )


def infer_unaryop(self, context=context_mod.context_ins, inferred_attr=None):
    inferred = self.prepare_inferred_value(inferred_attr, "operand", context)
    for val in self.get_inferred(inferred["operand"]):
        for res in _infer_unaryop(self.op, val, context):
            res += val
            yield res


def infer_const_unaryop(self, op, _, context):
    func = UNARY_METHOD.get(op)
    if func:
        yield from const_factory(func(self.value))
        return
    yield InferenceResult.load_result(nodes.Uninferable())


def infer_inst_unaryop(self, _, method_name, context=context_mod.context_ins):
    method = self.dunder_lookup(method_name)
    if method:
        context.map_args_to_func(self, func_node=method)
        yield from method.infer_return_value(context)
        return
    yield InferenceResult.load_result(nodes.Uninferable())


nodes.Const._infer_unaryop = infer_const_unaryop
nodes.NameConstant._infer_unaryop = infer_const_unaryop
nodes.ClassInstance._infer_unaryop = infer_inst_unaryop
nodes.UnaryOp._infer = infer_unaryop


def infer_boolop(self: nodes.BoolOp, context=context_mod.context_ins, inferred_attr=None):
    """
    - 'and' and 'or' evaluates expression from left to right.
    - with and, if all values are True, returns the last evaluated value. If any value is false, returns the first one.
    - or returns the first True value. If all are False, returns the last value

    ALl the following elements are False:
    [/] = implemented, [x] = pending.
    [/] None
    [/] False
    [/] 0 (whatever type from integer, float to complex)
    [/] Empty collections: “”, (), [], {}
    [x] Objects from classes that have the special method __nonzero__
    [x] Objects from classes that implements __len__ to return False or zero
    """

    def should_return(op, inf_result):
        if op == "or" and inf_result.strip_inference_result() is True:
            return True
        elif op == "and" and inf_result.strip_inference_result() is False:
            return True
        return False

    inferred = self.prepare_inferred_value(inferred_attr, "values", context)
    for vals in utilities.infer_product(*inferred["values"]):
        if all(
            map(
                lambda x: isinstance(
                    x.result, (nodes.Const, nodes.NameConstant, nodes.ClassInstance, nodes.BaseContainer)
                ),
                vals,
            )
        ):
            _cache = {}
            considered_vals = []
            yielded = False
            for v in vals:
                # called bool(v) to see which value to return
                if v.status:
                    bool_node = v.result.wrap_bool()
                    MANAGER.add_weak_ref(bool_node)
                    bool_status = next(bool_node.infer(context))
                    if should_return(self.op, bool_status):
                        # TODO: add test for bound conditions for short circuit operation
                        yield InferenceResult.from_other(v, inference_results=considered_vals)
                        yielded = True
                        break
                considered_vals.append(v)
            if not yielded:
                # return the last element
                yield InferenceResult.from_other(vals[-1], inference_results=considered_vals)
        else:
            res = InferenceResult.load_result(nodes.Uninferable(self), inference_results=vals)
            yield res


nodes.BoolOp._infer = infer_boolop


def infer_assignment(self, context=context_mod.context_ins, inferred_attr=None):
    """infer variable that is being assigned (AssignName and AssignAttribute"""
    stmt = self.statement()
    yield from stmt.value.infer(context=context)


nodes.AssignName._infer = infer_assignment
nodes.AssignAttribute._infer = infer_assignment


def infer_augassign(self: nodes.AugAssign, context=context_mod.context_ins, inferred_attr=None):
    """
    E.g.
    a += 2
    inferring this node will yield the value of `a`
    """
    inferred = self.prepare_inferred_value(inferred_attr, ("value",), context)
    scope = self.target.instance()
    ver = self.target.version - 1
    if ver < 0:
        yield InferenceResult.load_result(nodes.Uninferable(self))
        return
    node = scope.locals["{}_{}".format(self.target.get_base_var(), ver)]
    for lhs, rhs in utilities.infer_product(node.infer(context), inferred["value"]):
        for res in _infer_binary_op(lhs, rhs, self.op, context):
            res = res + lhs + rhs
            yield res


nodes.AugAssign._infer = infer_augassign


def infer_binop(self, context=context_mod.context_ins, inferred_attr=None):
    inferred = self.prepare_inferred_value(inferred_attr, ("left", "right"), context)
    for lhs, rhs in utilities.infer_product(inferred["left"], inferred["right"]):
        # checking of lhs and rhs type and flow of bin op here
        yield from _infer_binary_op(lhs, rhs, self.op, context)


def _infer_binary_op(left: InferenceResult, right: InferenceResult, op, context):
    methods = _bin_op_methods(left, right, op, context)
    # In mixed arithmetic operation, the operand with the "narrower" type
    # is widened to that of the other, where integer is narrower than
    # floating point, which is narrower than complex.
    # In this case, if any of the yield a value, that is the result.
    # or if all of the method yield a type, the "widest" type will be the result.
    results = []
    # when the first method has successfully yield some value (status=True),
    # this flag will help to skip the next method
    yielded = False
    for meth in methods:
        if not yielded:
            for res in meth():
                if res.status is True:
                    yielded = True
                    yield res
                else:
                    results.append(res)
    if yielded:
        return
    elif len(results) == 0:
        yield InferenceResult.load_result(nodes.Uninferable())
        return
    included_type = ("int", "float", "complex")
    TYPE_PRECEDENCE = enum.Enum("TYPE_PRECEDENCE", "{}".format(" ".join(included_type)))
    yield sorted(
        results,
        key=lambda a: TYPE_PRECEDENCE[a.result_type.name].value
        if (hasattr(a.result_type, "name") and a.result_type.name in included_type)
        else -1,
    )[-1]


def _bin_op_methods(left: InferenceResult, right: InferenceResult, op, context):
    """To yield different combination of dunder method calling"""
    if left.result_type is right.result_type:
        methods = [
            functools.partial(
                _invoke_op_inference,
                instance=left,
                method_name=BIN_OP_DUNDER_METHOD[op],
                other=right,
                op=op,
                infer_method_repr="_infer_binop",
                context=context,
            )
        ]
    else:
        methods = [
            functools.partial(
                _invoke_op_inference,
                instance=left,
                method_name=BIN_OP_DUNDER_METHOD[op],
                other=right,
                op=op,
                infer_method_repr="_infer_binop",
                context=context,
            ),
            functools.partial(
                _invoke_op_inference,
                instance=right,
                method_name=REFLECTED_BIN_OP_DUNDER_METHOD[op],
                other=left,
                op=op,
                infer_method_repr="_infer_binop",
                context=context,
            ),
        ]
    return methods


def _invoke_op_inference(
    instance: InferenceResult, method_name, other: InferenceResult, op, infer_method_repr, context
):
    """find the dunder method and call _infer_binop"""
    if isinstance(instance.result, nodes.Uninferable) or isinstance(other.result, nodes.Uninferable):
        # one of the operand's failed to infer. yield NonInference
        yield InferenceResult.load_result(
            nodes.Uninferable(override_msg="operation {} failed with left: {}, right: {}".format(op, instance, other)),
            inference_results=(instance, other),
        )
    elif instance.status and other.status:
        try:
            infer_method = getattr(instance.result, infer_method_repr)
            # the metadata of result for instance and other will be handled in the infer_bin_op
            # operation respectively, since they are some situation where we don't want to
            # append the bound_conditions
            yield from infer_method(op, other, method_name, context=context, self_result=instance)
        except (exceptions.VariableNotExistStackError, AttributeError):
            # Dunder method is unimplemented
            yield InferenceResult.load_result(
                nodes.Uninferable(
                    override_msg="Dunder method {} is unimplemented in instance: {}".format(
                        method_name, instance.result
                    )
                ),
                inference_results=(instance, other),
            )
    else:
        # one of the operand's value is unknown. yield InferenceResult with the type
        if instance.result_type is not None:
            method = instance.result_type.dunder_lookup(method_name)
            if context.config.is_type_inference() and method is not None:
                yield InferenceResult.load_type(method.get_return_type(), inference_results=(instance, other))

            else:
                yield InferenceResult.load_result(
                    nodes.Uninferable(
                        override_msg="operation {} failed with left: {}, right: {}".format(op, instance, other)
                    ),
                    inference_results=(instance, other),
                )


def infer_const_bin_op(self, op, other, _, context=None, self_result=None):
    def fail():
        yield InferenceResult.load_result(
            nodes.Uninferable(override_msg="operation {} failed with left: {}, right: {}".format(op, self, other))
        )

    func = BIN_OP_METHOD[op]
    try:
        if not isinstance(other.result, (nodes.Const, nodes.NameConstant)):
            return fail()
        result = func(self.value, other.result.value)
        for res in const_factory(result):
            res = res + other + self_result
            yield res
    except Exception:
        return fail()


def infer_inst_bin_op(self, _, other, method_name, context=context_mod.context_ins, self_result=None):
    method = self.dunder_lookup(method_name)
    context.map_args_to_func(self, other.result, func_node=method)
    for res in method.infer_return_value(context):
        res = res + other + self_result
        yield res


def infer_container_bin_op(self, op, other, _, context=context_mod.context_ins, self_result=None):
    func = BIN_OP_METHOD[op]
    for left, right in utilities.infer_product(self.extract_const(context), other.result.extract_const(context)):

        # if the operator is * and one of the operand is 0, should yield the empty container
        # without metadata from the container's. we'll yield multiple empty list if `self`
        # actually have many possibilities, but decorators will help us filter the result.
        # We'll do a if else check, looks ugly, but we don't have many more situation to cover either
        left_result = left.strip_inference_result()
        right_result = right.strip_inference_result()
        if op == "*" and type(right_result) is int and right_result == 0:
            if utilities.check_selected_operand((other, right)):
                if isinstance(left_result, (list, tuple)):
                    yield InferenceResult.load_result(
                        container_factory(type(left_result)()), inference_results=(other, right)
                    )
                else:
                    yield InferenceResult.load_result(
                        nodes.Uninferable(self), inference_results=(self_result, other, left, right)
                    )
        else:
            if utilities.check_selected_operand((self_result, other, left, right)):
                try:
                    yield InferenceResult.load_result(
                        container_factory(func(left_result, right_result)),
                        inference_results=(self_result, other, left, right),
                    )
                except Exception:
                    yield InferenceResult.load_result(
                        nodes.Uninferable(self), inference_results=(self_result, other, left, right)
                    )


nodes.BinOp._infer = infer_binop
nodes.Const._infer_binop = infer_const_bin_op
nodes.NameConstant._infer_binop = infer_const_bin_op
nodes.BaseContainer._infer_binop = infer_container_bin_op
nodes.ClassInstance._infer_binop = infer_inst_bin_op


def infer_global_name(self, context=context_mod.context_ins, inferred_attr=None):
    """Infer a name object that look at the global scope"""
    # only infer if `self` is Name and most importantly not an Attribute
    if not isinstance(self, nodes.Name):
        return
    try:
        if context is not None:
            stmt = context.globals_context.get_latest_stmt(str(self))
            if stmt:
                yield from stmt.infer(context)
    except exceptions.VariableNotExistStackError:
        try:
            # if everything yield no result (globals, locals),
            # it will resort recursively look for definition outside of the scope
            # In some cases when not all part of the outer scope is available to the current scope
            # e.g. when a function is called between the module, the definition after the call won't be
            # available in the function scope, though this has been handled specifically by reloading
            # to the context.globals_context
            value = self.get_from_outer(str(self.id), skip=1)
            yield from value.infer(context)
        except exceptions.VariableNotExistStackError:
            yield InferenceResult.load_result(
                nodes.Uninferable(
                    self,
                    override_msg="""\
            variable: {} is not defined""".format(
                        self.get_var_repr()
                    ),
                )
            )


def infer_name(self, context=context_mod.context_ins, inferred_attr=None):
    if self.links is None:
        # might be referring to globals
        for global_name in infer_global_name(self, context):
            if isinstance(global_name.result, nodes.Uninferable):
                # can't resolve the function, look in python standard library
                builtin_mod = MANAGER.builtins_tree.locals.get(self.get_var_repr())
                if builtin_mod:
                    yield from builtin_mod.infer(context)
                    return
            yield global_name
    else:
        bound_conditions = self.get_bound_conditions()
        for res in self.links.infer(context=context):
            yield InferenceResult.from_other(res, bound_conditions=bound_conditions)


def infer_attribute(self, context=context_mod.context_ins, inferred_attr=None):
    def _infer(ins, _linked_res):
        context.instance_mode = old_instance_mode
        if isinstance(ins.result, nodes.Uninferable):
            yield ins
            return
        context.bound_instance = ins.result
        # must be referring to attribute in constructor, see #mr8y0

        bound_conditions = self.get_bound_conditions()
        if _linked_res:
            yield InferenceResult.from_other(_linked_res, bound_conditions, inference_results=(ins,))
        else:
            if ins.result:
                stmt = ins.result.get_latest_stmt(self.get_var_repr())
                for stmt_res in stmt.infer(context):
                    # this infer() is without load_result. Need to load the bound conditions manually
                    bound_conditions = self.get_bound_conditions()
                    if utilities.check_selected_operand((stmt_res, ins)):
                        yield InferenceResult.from_other(stmt_res, bound_conditions, inference_results=(ins,))

    inferred = self.prepare_inferred_value(inferred_attr, fields=("value", "links"), context=context)
    old_instance_mode = context.instance_mode
    context.instance_mode = True

    def yield_links():
        # temporary change instance mode to old instance mode
        context.instance_mode = old_instance_mode
        yield from self.get_inferred(inferred["links"])
        context.instance_mode = True

    # first, we get the inferred for `value`, this is to get the bound instance
    # e.g. for `c = Kls(); c.foo()`, we need to get the instance for `c`, in order to
    # insert it into bound method.
    for ins, linked_res in utilities.infer_product(self.get_inferred(inferred["value"]), yield_links()):
        try:
            # if the inferred result is not an instance(i.e. with locals),
            # it's not possible to infer the attribute. Simply yield uninferable.
            if isinstance(ins.result, (nodes.LocalsDictNode, nodes.BaseInstance)):
                yield from _infer(ins, linked_res)
            else:
                context.instance_mode = old_instance_mode
                yield InferenceResult.load_result(nodes.Uninferable(self), inference_results=(ins,))
        except exceptions.VariableNotExistStackError:
            # base instance (self.value.instance()) does not contain
            # the definition for this attribute. Search in the global scope.
            try:
                for ins in infer_global_name(self.value, context):
                    yield from _infer(ins, linked_res)
            except exceptions.VariableNotExistStackError:
                context.instance_mode = old_instance_mode
                yield InferenceResult.load_result(nodes.Uninferable(self), inference_results=(ins,))
    context.instance_mode = old_instance_mode


nodes.Name._infer = infer_name
nodes.Attribute._infer = infer_attribute


def infer_phi(self: nodes.Phi, context=context_mod.context_ins, inferred_attr=None):
    # hash the ifexp as well because phi and ifexp is served as the pivot point
    # for variable having different value. Different phi/ifexp will have different
    # set of value
    call_chains = context.get_call_node_chain(self)
    result_hash = hash((self, frozenset(context.inverted_conds), tuple(call_chains)))
    for val in self.value:
        # this value might get replaced by other value in this phi function.
        curr_bound = set()
        if val.links:
            curr_bound = val.links.statement().get_bound_conditions()
        pre_inverted_condtiions = set()
        bound_conditions = set()
        if val in self.replaced_map:
            for replaced_val in self.replaced_map[val]:
                if replaced_val.links:
                    replaced_stmt = replaced_val.links.statement()
                    r_bound = replaced_stmt.get_bound_conditions()
                    r_bound -= curr_bound
                    # remove any bound that is already part of bound in previous replacement.
                    # this will happen when there is multiple elif situation, and subsequent elif's
                    # bound conditions will include negate of previous elif's bound, thus making it unsat
                    r_bound -= bound_conditions
                    pre_inverted_condtiions |= r_bound
                    r_bound_inverted = set(r_b.invert_condition() for r_b in r_bound)
                    if len(r_bound_inverted) > 1:
                        # need to wrap it in Or() since it's inverted
                        bool_node = nodes.BoolOp()
                        bool_node.postinit("or", list(r_bound_inverted))
                        MANAGER.add_weak_ref(bool_node)
                        bound_conditions.add(bool_node)
                    else:
                        bound_conditions |= r_bound_inverted
        for res in val.infer(context):
            yield InferenceResult.from_other(
                res,
                selected_operand={result_hash: res},
                bound_conditions=bound_conditions,
                inverted_conditions=pre_inverted_condtiions,
            )


nodes.Phi._infer = infer_phi


def infer_call(self: nodes.Call, context=context_mod.context_ins, inferred_attr=None):
    try:
        ins = next(self.get_target_instance()).instance_dict.get(self)
    except (exceptions.InstanceNotExistError, StopIteration, AttributeError):
        ins = None
        MANAGER.logger.warning("INFER", "failed to get target_instance of node: ", self)
    bound_conditions = self.get_bound_conditions()
    for target_func in self.func.infer(context):
        if isinstance(target_func.result, nodes.Uninferable):
            if context.instance_mode is True:
                # if instance_mode is True, means that in this stage, the function
                # definition can't be resolved, therefore there is no need to
                # map the arguments before return the instance
                if ins:
                    ins.resolve_instance(context, resolve_constructor=True)
                    yield InferenceResult.load_result(ins, inference_results=(target_func,))
                    return
            # bound_conditions will need to include the bound conditions for args as well.
            # if target_func is valid, the args.bound_conditions will get included in the
            # target_func return node analysis.
            # args will not get resolve, instead, the node will get inserted in the call context,
            # and only resolve lazily in the target_func. So we need to resolve it here to get the
            # bound conditions.
            yielded = False
            args = self.args + [kw.value for kw in self.keywords]
            for args_res in utilities.infer_product(*(arg.infer(context) for arg in args)):
                res = InferenceResult.load_result(
                    nodes.Uninferable(override_msg="can't resolve call to {}".format(self.func)),
                    inference_results=(*args_res, target_func),
                    bound_conditions=bound_conditions,
                )
                yielded = True
                yield res
            if not yielded:
                yield InferenceResult.load_result(
                    nodes.Uninferable(override_msg="can't resolve call to {}".format(self.func)),
                    bound_conditions=bound_conditions,
                    inference_results=(target_func,),
                )
        else:
            target_func_result = target_func.result
            context.reload_context(self, target_func_result, target_func.bound_instance, ins)
            if context.instance_mode is True:
                if ins:
                    ins.resolve_instance(context, resolve_constructor=True)
                    yield InferenceResult.load_result(
                        ins, bound_conditions=bound_conditions, inference_results=(target_func,)
                    )
                else:
                    yield InferenceResult.load_result(
                        nodes.Uninferable(override_msg="can't resolve call to {}".format(self.func)),
                        bound_conditions=bound_conditions,
                        inference_results=(target_func,),
                    )
            else:
                if ins is not None:
                    ins.merge_cls(target_func_result)
                if isinstance(target_func_result, nodes.ClassDef) and ins is not None:
                    # it's a call to a class
                    yield InferenceResult.load_result(
                        ins, bound_conditions=bound_conditions, inference_results=(target_func,)
                    )
                elif isinstance(target_func_result, nodes.OverloadedFunc):
                    for func in target_func_result.elts:
                        # continue to map until it matches
                        offset = 1 if func.type == "method" else 0
                        context.add_call_chain(self, func)
                        results = []
                        if context.map_args_to_func(*self.args, func_node=func, remove_default=False, offset=offset):
                            for fr in func.infer_return_value(context):
                                results.append(
                                    InferenceResult.from_other(fr, bound_conditions, inference_results=(target_func,))
                                )
                        context.remove_call_chain(self)
                        yield from results
                        # no matches in all @overload stmt. Use the recent definition.
                        func = target_func_result.elts[-1]
                        context.add_call_chain(self, func)
                        results = []
                        for func_result in func.infer_return_value(context):
                            func_result += target_func
                            func_result.bound_conditions |= bound_conditions
                            results.append(func_result)
                        context.remove_call_chain(self)
                        yield from results
                elif isinstance(target_func_result, nodes.FunctionDef):
                    context.add_call_chain(self, target_func_result)
                    results = []
                    for func_result in target_func_result.infer_return_value(context):
                        results.append(
                            InferenceResult.from_other(
                                func_result, bound_conditions=bound_conditions, inference_results=(target_func,)
                            )
                        )
                    context.remove_call_chain(self)
                    yield from results
                elif isinstance(target_func_result, nodes.Lambda):
                    for func_result in target_func_result.infer_return_value(context):
                        yield InferenceResult.from_other(
                            func_result, bound_conditions=bound_conditions, inference_results=(target_func,)
                        )
                else:
                    yield InferenceResult.load_result(
                        nodes.Uninferable(override_msg="can't resolve call to {}".format(self.func)),
                        bound_conditions=bound_conditions,
                        inference_results=(target_func,),
                    )


nodes.Call._infer = infer_call


def infer_arg(self, context=context_mod.context_ins, inferred_attr=None):
    def _get_type(ins):
        if hasattr(ins.annotation, "infer"):
            for type_def_node in ins.annotation.infer(context):
                if type_def_node.status:
                    type_def_node = type_def_node.result
                    if type_def_node.name in BUILT_IN_TYPE and type_def_node == MANAGER.builtins_tree.locals.get(
                        type_def_node.name
                    ):
                        return InferenceResult.load_type(overwrite_type=type_def_node)
        return InferenceResult.load_result(
            nodes.Uninferable(
                override_msg="""\
            Variable {} is uninferable since there is no calling context and variable is unannotated\
            """.format(
                    self
                )
            )
        )

    if context is None:
        # try to at least infer the type
        yield _get_type(self)
    else:
        arg = context.call_context.get(self)
        if arg is None:
            if context.instance_mode is True:
                ins = self.scope().instance_dict.get(self)
                if ins:
                    yield InferenceResult.load_result(ins)
                    return
            # get the default value
            val = self.get_default()
            if val is None:
                # try to infer the type
                if context.config.is_type_inference():
                    yield _get_type(self)
            else:
                yield from val.infer(context)
        else:
            yield from arg.infer(context)


nodes.Arg._infer = infer_arg


def infer_compare(self, context=context_mod.context_ins, inferred_attr=None):
    inferred = self.prepare_inferred_value(inferred_attr, ("left", "comparators"), context)
    for comp in utilities.infer_product(*(inferred["left"], *(comp for comp in inferred["comparators"]))):
        if any((not c.status for c in comp)):
            if context.config.is_type_inference():
                res = InferenceResult.load_type(bool)
                for c in comp:
                    res += c
                yield res
            else:
                yield InferenceResult.load_result(nodes.Uninferable(), inference_results=comp)
        else:
            for result in calc_compare(comp, self.ops, context):
                for c in comp:
                    result += c
                yield result


def _comp_op_methods(left: InferenceResult, right: InferenceResult, op, context):
    """To yield different combination of dunder method calling
    In compare node, we don't care about the type since there is no reflected
    dunder method in comparison op.
    """
    methods = [
        functools.partial(
            _invoke_op_inference,
            instance=left,
            method_name=COMP_OP_DUNDER_METHOD[op],
            other=right,
            op=op,
            infer_method_repr="_infer_comp_op",
            context=context,
        )
    ]
    if op in COMP_REFLECTED_OP:
        reflected_op = COMP_REFLECTED_OP[op]
        methods.append(
            functools.partial(
                _invoke_op_inference,
                instance=right,
                method_name=COMP_OP_DUNDER_METHOD[reflected_op],
                other=left,
                op=reflected_op,
                infer_method_repr="_infer_comp_op",
                context=context,
            )
        )
    return methods


def calc_compare(comp_list, op_list, context):
    """
    return the result of comp_list and op_list, assuming comp_list[0] is left,
    and all value in comp_list is constant
    """
    # get the result of InferenceResult
    left = comp_list[0]
    result = nodes.BoolOp()
    MANAGER.add_weak_ref(result)
    operands = []
    for comp, op in zip(comp_list[1:], op_list):
        methods = _comp_op_methods(left, comp, op, context)
        yielded = False
        for meth in methods:
            try:
                val = next(meth())
            except StopIteration:
                continue
            if isinstance(val.result, nodes.Uninferable):
                # try for the next method
                continue
            operands.append(val.result)
            yielded = True
            break
        if not yielded:
            yield InferenceResult.load_result(
                nodes.Uninferable(override_msg=f"Compare failed with left: {left}, right: {comp}")
            )
            return
        left = comp
    result.postinit(op="and", values=operands)
    MANAGER.apply_transform(result)
    yield from result.infer(context)


def infer_const_comp_op(self, op, other, _, context=None, self_result=None):
    meth = COMP_METHOD[op]
    try:
        tuples = list(utilities.infer_product(self.extract_const(), other.result.extract_const()))
        for left, right in tuples:
            try:
                result = meth(left.strip_inference_result(), right.strip_inference_result())
                yield from const_factory(result)
            except TypeError:
                yield InferenceResult.load_result(
                    nodes.Uninferable(
                        override_msg="operation {} failed with left: {}, right: {}".format(
                            op, self.value, other.result.value
                        )
                    ),
                    inference_results=(left, right),
                )
        if not tuples:
            yield InferenceResult.load_result(
                nodes.Uninferable(
                    override_msg="operation {} failed with left: {}, right: {}".format(
                        op, self.value, other.result.value
                    )
                )
            )
    except NotImplementedError:
        yield InferenceResult.load_result(
            nodes.Uninferable(
                override_msg="operation {} failed with left: {}, right: {}".format(op, self.value, other.result.value)
            )
        )


@contextlib.contextmanager
def _make_call_from_dunder_method(instance, dunder_method, context, *args):
    call_node = nodes.Call()
    # TODO: handle the scope of the function call
    call_node.locals["scope"] = {}
    context.bound_instance = instance
    call_node.postinit(func=dunder_method, args=args)
    MANAGER.add_weak_ref(call_node)
    yield call_node
    context.bound_instance = None


def infer_inst_comp_op(self, _, other, method_name, context=context_mod.context_ins, self_result=None):
    # create a `Call` node and infer it from there
    method = self.dunder_lookup(method_name)
    if method:
        with _make_call_from_dunder_method(self, method, context, other.result) as call_node:
            yield from call_node.infer(context)
    else:
        yield InferenceResult.load_result(nodes.Uninferable(self))


nodes.Const._infer_comp_op = infer_const_comp_op
nodes.NameConstant._infer_comp_op = infer_const_comp_op
nodes.ClassInstance._infer_comp_op = infer_inst_comp_op
nodes.Compare._infer = infer_compare


def infer_bool(self: nodes.Bool, context=context_mod.context_ins, inferred_attr=None):
    for val in self.value.infer(context):
        try:
            infer_method = getattr(val.result, "_infer_bool")
            for res in infer_method(context=context):
                res += val
                yield res
        except AttributeError:
            # Dunder method is unimplemented
            yield InferenceResult.load_result(
                nodes.Uninferable(override_msg=f"infer_bool infer method is not defined for node: {type(val.result)}"),
                inference_results=(val,),
            )


def infer_const_bool(self: nodes.Const, context=context_mod.context_ins):
    yield from const_factory(bool(self.value))


def infer_inst_bool(self: nodes.ClassInstance, context=context_mod.context_ins):
    """
    reference: https://docs.python.org/3/reference/datamodel.html#object.__bool__
    First we'll try __bool__, if the method does not exist, we'll try __len__, and it's True
    if it return non zero. The instance is True when both of the method doesn't exist
    """
    yielded = False
    for meth in ("__bool__", "__len__"):
        try:
            method = self.dunder_lookup(meth)
            if method:
                yielded = True
                with _make_call_from_dunder_method(self, method, context) as call_node:
                    yield from call_node.infer(context)
                break
        except (exceptions.VariableNotExistStackError, AttributeError):
            pass
    if not yielded:
        # both method does not exist. Default to True
        yield InferenceResult.load_result(nodes.Const(True))


def infer_sequence_bool(self: nodes.Sequence, context=context_mod.context_ins):
    yield InferenceResult.load_result(bool(self.elts))


def infer_dict_bool(self: nodes.Dict, context=context_mod.context_ins):
    yield InferenceResult.load_result(bool(self.keys))


nodes.Const._infer_bool = infer_const_bool
nodes.NameConstant._infer_bool = infer_const_bool
nodes.ClassInstance._infer_bool = infer_inst_bool
nodes.Sequence._infer_bool = infer_sequence_bool
nodes.Dict._infer_bool = infer_dict_bool
nodes.Bool._infer = infer_bool


def infer_const_builtins(self: nodes.Const, builtin_func: str, context):
    builtin = getattr(builtins, builtin_func)
    result = builtin(self.value)
    yield from const_factory(result)


def infer_inst_builtins(self: nodes.ClassInstance, builtin_func: str, context):
    builtin_dunder_func_repr = "__" + builtin_func + "__"
    yielded = False
    try:
        method = self.dunder_lookup(builtin_dunder_func_repr)
        if method:
            with _make_call_from_dunder_method(self, method, context) as call_node:
                yielded = True
                yield from call_node.infer(context)
    except (exceptions.VariableNotExistStackError, AttributeError):
        pass
    if not yielded:
        yield InferenceResult.load_result(nodes.Uninferable(self))


def infer_container_builtins(self: nodes.BaseContainer, builtin_func: str, context):
    builtin = getattr(builtins, builtin_func)
    result = builtin(self)
    yield from const_factory(result)


nodes.Const._infer_builtins = infer_const_builtins
nodes.NameConstant._infer_bulitins = infer_const_builtins
nodes.ClassInstance._infer_builtins = infer_inst_builtins
nodes.BaseContainer._infer_builtins = infer_container_builtins


def infer_index(self, context=context_mod.context_ins, inferred_attr=None):
    yield from self.value.infer(context)


nodes.Index._infer = infer_index


def infer_slice(self, context=context_mod.context_ins, inferred_attr=None):
    lower = self.lower.infer(context) if self.lower is not None else (None,)
    upper = self.upper.infer(context) if self.upper is not None else (None,)
    step = self.step.infer(context) if self.step is not None else (None,)
    for lower, upper, step in utilities.infer_product(lower, upper, step):
        low = lower.result.value if lower else None
        up = upper.result.value if upper else None
        st = step.result.value if step else None
        for res in const_factory(slice(low, up, st)):
            res += lower + upper + step
            yield res


nodes.Slice._infer = infer_slice


def infer_subscript(self, context=context_mod.context_ins, inferred_attr=None):
    if self.links is None:
        # take the default value from the list
        for val in self.value.infer(context):
            if isinstance(val.result, nodes.Uninferable):
                yield InferenceResult.load_result(nodes.Uninferable(self), inference_results=(val,))
                return
            if not (isinstance(val.result, (nodes.List, nodes.Tuple, nodes.Dict))):
                yield InferenceResult.load_result(nodes.Uninferable(self), inference_results=(val,))
                return
            for sl in self.slice.infer(context):
                if sl.status is False or not isinstance(sl.result, nodes.Const):
                    yield InferenceResult.load_result(nodes.Uninferable(self), inference_results=(val, sl))
                    return
                for res in val.result.getitem(sl.result.value, context):
                    res += val + sl
                    yield res
    else:
        # there exist new assignment to this node
        yield from self.links.infer(context=context)


nodes.Subscript._infer = infer_subscript


def getitem_sequence(self, index, context=context_mod.context_ins):
    if isinstance(index, slice):
        new_c = self.__class__()
        new_c.elts = self.elts[index]
        new_c.parent = self.parent
        yield InferenceResult.load_result(new_c)
    else:
        try:
            for val in self.elts[index].infer(context):
                yield val
        except IndexError:
            MANAGER.logger.warning("INFER", "Failed to get index: {} for item: {}", index, self)


def getitem_dict(self, index, context=context_mod.context_ins):
    if isinstance(index, slice):
        raise exceptions.OperationIncompatible("getitem dict", index)
    actual_index = self.get_key_index(index, context)
    if actual_index is not None:
        yield from self.values[actual_index].infer(context)
    else:
        yield InferenceResult.load_result(nodes.Uninferable(self))


nodes.Sequence.getitem = getitem_sequence
nodes.Dict.getitem = getitem_dict


def infer_killvarcall(self, context=context_mod.context_ins, inferred_attr=None):
    """Infer the latest KILL variable of the func that is called"""
    # get the latest stmt associate with the variable
    # get the instance at any target
    func = next(self.value.func.infer(context)).result
    stmt = self.value_scope.get_latest_stmt(self.var)
    context.map_call_node_to_func(self.value, func)
    context.reload_context(self.value, func)
    context.add_call_chain(self, func)
    if func.type == "method":
        # insert instance into the `self` param. We can't use the original instance
        # as it contains all the locals. Instead, use the locals provided in the call stmt. See (#q2qaq)
        self_ins = nodes.LocalsDictNode()
        self_ins.locals = self.value.locals["instance"]
        self_ins.ssa_record = self.value.ssa_record
        context.map_args_to_func(self_ins, func_node=func, remove_default=False)
        context.globals_context.locals = self.value.locals["scope"]
    yield from stmt.infer(context)
    context.remove_call_chain(self)


nodes.KillVarCall._infer = infer_killvarcall


def infer_temp_instance(self, context=context_mod.context_ins, inferred_attr=None):
    """
    try to get the instance from arg that passed in.
    E.g.
    def foo(a):
        return a.b.c
    This will create temp instance (i.e. UselessStub) for a.b
    When inferring the real value though, the real instance (a.b) is needed and can get from arguments
    that are passing in.
    """
    if context.instance_mode is False:
        # get the LocalsDictNode(created temp) associate with this node
        ins = self.scope().instance_dict.get(self)
        if ins:
            yield InferenceResult.load_result(ins)
        else:
            yield InferenceResult.load_result(nodes.Uninferable(self))
    else:
        # get the instance at any target
        ins = next(self.get_target_instance()).instance_dict.get(self)
        if ins:
            yield InferenceResult.load_result(ins)


nodes.TempInstance._infer = infer_temp_instance


def infer_ifexp(self, context=context_mod.context_ins, inferred_attr=None):
    """
    running:
    1 if x else 2
    will yield 1, 2
    """
    # hash the ifexp as well because phi and ifexp is served as the pivot point
    # for variable having different value. Different phi/ifexp will have different
    # set of value
    call_chains = context.get_call_node_chain(self)
    result_hash = hash((self, frozenset(context.inverted_conds), tuple(call_chains)))
    for res in self.body.infer(context):
        yield InferenceResult.from_other(res, bound_conditions={self.test}, selected_operand={result_hash: res})
    for res in self.orelse.infer(context):
        inverted_condition = self.test.invert_condition()
        yield InferenceResult.from_other(
            res, bound_conditions={inverted_condition}, selected_operand={result_hash: res}
        )


nodes.IfExp._infer = infer_ifexp


def infer_import(self, context=context_mod.context_ins, inferred_attr=None):
    ins = self.scope().instance_dict.get(self)
    if ins:
        yield InferenceResult.load_result(ins)
    else:
        yield InferenceResult.load_result(nodes.Uninferable(self))


nodes.ImportFrom._infer = nodes.Import._infer = infer_import


def infer_sequence(
    self: Union[nodes.List, nodes.Set, nodes.Tuple], context=context_mod.context_ins, inferred_attr=None
):
    inferred = self.prepare_inferred_value(inferred_attr, "elts", context)
    if MANAGER.config.enable_infer_sequence:
        initial_bound_conditions = self.get_bound_conditions()
        for vals in utilities.infer_product(*(inferred["elts"])):
            extracted_vals = []
            status = True
            for v in vals:
                if v.status:
                    extracted_vals.append(v.strip_inference_result())
                else:
                    status = False
                    yield InferenceResult.load_result(
                        nodes.Uninferable(), bound_conditions=initial_bound_conditions, inference_results=vals
                    )

            if status:
                yield InferenceResult.load_result(
                    container_factory(self.get_actual_type()(extracted_vals)),
                    bound_conditions=initial_bound_conditions,
                    inference_results=vals,
                )
    else:
        yield from infer_end(self, context, inferred_attr)


nodes.Sequence._infer = infer_sequence
# FIXME infer definition specifically for dict as it can't be shared with sequence
nodes.Dict._infer = infer_end


# ----------------type stub area---------------------
def infer_typestub(self: nodes.TypeStub, context=context_mod.context_ins, inferred_attr=None):
    if self.value:
        yield from self.value.infer(context)
    else:
        yield InferenceResult.load_type(self.type.get_built_in_type())


nodes.TypeStub._infer = infer_typestub
nodes.OverloadedFunc._infer = infer_end
# ----------------end type stub are---------------------
CONST_MAP = {
    int: nodes.Const,
    float: nodes.Const,
    bool: nodes.NameConstant,
    str: nodes.Const,
    complex: nodes.Const,
    bytes: nodes.Const,
    slice: nodes.Const,
    list: nodes.Const,
    set: nodes.Const,
    tuple: nodes.Const,
    type(None): nodes.NameConstant,
}

CONTAINER_MAP = {set: nodes.Set, list: nodes.List, tuple: nodes.Tuple}


def const_factory(value, *args, **kwargs):
    """return nodes equivalent of const value.
    Will yield all combination of the content of the list
    """
    constructor = CONST_MAP.get(value.__class__)
    if constructor is None:
        if hasattr(value, "infer"):
            yield from value.infer()
        else:
            yield InferenceResult.load_result(nodes.Uninferable(value), *args, **kwargs)
    else:
        yield InferenceResult.load_result(constructor(value), *args, **kwargs)


def container_factory(container):
    # convert elem in container to Const
    constructor = CONTAINER_MAP[container.__class__]
    new_container_elts = []
    # also make set iterable
    for elem in list(container):
        elem_constructor = CONST_MAP.get(elem.__class__)
        if elem_constructor:
            new_container_elts.append(elem_constructor(elem))
        else:
            new_container_elts.append(elem)
    new_container = constructor()
    new_container.elts = new_container_elts
    return new_container


def reverse_container_factory(container):
    # convert nodes.Const in the container to the python constant
    if isinstance(container, (list, set, tuple)):
        # also make set iterable
        constructor = CONTAINER_MAP[container.__class__]
        new_elts = []
        for elem in list(container):
            if not elem.status:
                raise exceptions.ContainerExtractError
            if isinstance(elem.result, (nodes.Const, nodes.NameConstant)):
                new_elts.append(elem.result.value)
            elif isinstance(elem.result, (nodes.ClassInstance)):
                new_elts.append(elem.result)
            else:
                new_elts.append(elem.result)
        new_container = constructor()
        new_container.elts = new_elts
        return new_container
    else:
        raise exceptions.ContainerExtractError


def limit_inference(iterator, size):
    """Limit inference amount.
    Limit inference amount to help with performance issues with
    exponentially exploding possible results.
    :param iterator: the inference iterator
    :type iterator: Iterator(BaseNode)
    :param size: Maximum mount of nodes yielded plus an
        Uninferable at the end if limit reached
    :type size: int
    :yields: A possibly modified generator
    :rtype param: Iterable
    """
    yield from itertools.islice(iterator, size)
    has_more = next(iterator, False)
    if has_more is not False:
        yield InferenceResult.load_result(nodes.Uninferable())


def inference_transform_wrapper(infer_function):
    """should return a transform function that change node._explicit_inference"""

    def transform(node, infer_function=infer_function):
        node.explicit_inference = infer_function
        return node

    return transform
