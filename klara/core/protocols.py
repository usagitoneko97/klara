"""Defined python's object behaviour e.g. dunder method definition and action"""
import ast
from typing import Iterable

from klara.core import exceptions, nodes
from klara.core.context_mod import InferenceContext
from klara.core.tree_rewriter import TreeRewriter


def instance_attr(self, context=None):
    if isinstance(self.value, nodes.Variable):
        call_ins = self.value.instance()
        value_repr = self.value.get_var_repr()
        if value_repr in call_ins.locals:
            context = context or InferenceContext(instance_mode=True)
            old_instance_mode = context.instance_mode
            context.instance_mode = True
            for ins in call_ins.locals[value_repr].infer(context):
                if ins.status is True:
                    context.instance_mode = old_instance_mode
                    return ins.result
                elif isinstance(ins.result, nodes.Uninferable) or ins.result is None:
                    # expect caller to catch this exception to pass on
                    # when rename attr instance that the `value` is not
                    # LocalsDictNode e.g. ta = ta[2:] is not valid instance,
                    # but list method can be applied, e.g. ta.find(1)
                    context.instance_mode = old_instance_mode
                    raise exceptions.InstanceNotExistError(self)
                context.instance_mode = old_instance_mode
        else:
            # it's probably coming from global or accessing attribute from argument
            raise exceptions.NotInLocalsError(value_repr, call_ins)
    elif isinstance(self.value, nodes.Call):
        # straight away get from instance_dict
        call_ins = self.value.instance()
        instance = call_ins.scope().instance_dict.get(self.value)
        if instance:
            return instance
        else:
            raise exceptions.InstanceNotExistError(self)
    elif isinstance(self.value, (nodes.Const, nodes.BaseContainer)):
        # for cases like "".format()
        # we can return the const directly since it contains
        # all the locals dict info
        return self.value
    else:
        raise NotImplementedError("attribute accessing of node type: {} is not supported.".format(type(self.value)))


def instance_scope(self, context=None):
    return self.scope()


def instance_starred(self, context=None):
    return self.value.instance(context)


nodes.Variable.instance = instance_scope
nodes.Attribute.instance = instance_attr
nodes.Starred.instance = instance_starred
nodes.Call.instance = instance_scope
nodes.Const.instance = instance_scope


def get_caller_arg(self, arg_str: str, call_node):
    """get the caller argument based on a str"""
    if self.parent.type == "method" and self.get_index_of_arg(arg_str) == 0:
        # return the instance
        context = InferenceContext(instance_mode=True)
        for ins in call_node.func.infer(context):
            if isinstance(ins.result, nodes.Uninferable) or ins.bound_instance is None:
                return []
            return ins.bound_instance.name
    return []


nodes.Arguments.get_caller_arg = get_caller_arg


BIN_OP_DUNDER_METHOD = {
    "+": "__add__",
    "-": "__sub__",
    "/": "__truediv__",
    "//": "__floordiv__",
    "*": "__mul__",
    "**": "__pow__",
    "%": "__mod__",
    "&": "__and__",
    "|": "__or__",
    "^": "__xor__",
    "<<": "__lshift__",
    ">>": "__rshift__",
    "@": "__matmul__",
}

COMP_OP_DUNDER_METHOD = {
    ">": "__gt__",
    "<": "__lt__",
    ">=": "__ge__",
    "<=": "__le__",
    "==": "__eq__",
    "!=": "__ne__",
    "in": "__contains__",
    "not in": "__contains__",
}

COMP_REFLECTED_OP = {
    ">": "<",
    "<": ">",
    "==": "!=",
    "!=": "==",
    ">=": "<=",
    "<=": ">=",
}

UNARY_OP_DUNDER_METHOD = {
    "-": "__neg__",
    "+": "__pos__",
    "~": "__invert__",
    "not": None,
}

DUNDER_METHOD = {**COMP_OP_DUNDER_METHOD, **BIN_OP_DUNDER_METHOD}


def _reflected_name(name):
    return "__r" + name[2:]


REFLECTED_BIN_OP_DUNDER_METHOD = {key: _reflected_name(value) for (key, value) in BIN_OP_DUNDER_METHOD.items()}

BIN_OP_METHOD = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "/": lambda a, b: a / b,
    "%": lambda a, b: a % b,
    "&": lambda a, b: a & b,
    "|": lambda a, b: a | b,
    "//": lambda a, b: a // b,
    "*": lambda a, b: a * b,
    "**": lambda a, b: a ** b,
    "^": lambda a, b: a ^ b,
    ">>": lambda a, b: a >> b,
    "<<": lambda a, b: a << b,
    "@": lambda a, b: a @ b,
}

UNARY_METHOD = {"+": lambda a: +a, "-": lambda a: -a, "not": lambda a: not a, "~": lambda a: ~a}

COMP_METHOD = {
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "in": lambda a, b: a in b,
    "not in": lambda a, b: a not in b,
}


def py2_div(a, b):
    if any(type(i) is float for i in (a, b)):
        return a / b
    else:
        return a // b


def _or(*val):
    res = False
    for x in val:
        res = res or x
    if res is False:
        return val[-1]
    return res


def _and(*val):
    res = True
    for x in val:
        res = res and x
    if res is True:
        return val[-1]
    return res


BOOL_METHOD = {"or": _or, "and": _and}


def get_custom_dunder_method(left: nodes.Variable, op: str, context: InferenceContext = None) -> Iterable[nodes.Proxy]:
    """return the custom dunder method for this operation, not include default dunder method
    Raise: DunderUnimplemented if no dunder method
    Raise: OperationIncompatible if :
            op is not comparison operator
            left is not Instance
    """
    for left_ins in left.infer(context):
        if left_ins.status is False:
            raise exceptions.OperationIncompatible(
                override_msg="couldn't get the actual instance of node: {}".format(left)
            )
        left_ins = left_ins.result
        try:
            if not isinstance(left_ins, nodes.ClassInstance):
                raise exceptions.OperationIncompatible(
                    override_msg="the node: {} is not of type ClassInstance".format(left_ins)
                )
            op_dunder = DUNDER_METHOD[op]
            method = left_ins.dunder_lookup(op_dunder)
            if method is None:
                raise exceptions.DunderUnimplemented(method_name=op_dunder, target_cls=left_ins)
            yield method
        except KeyError:
            raise exceptions.OperationIncompatible("get custom dunder method", op)
        except exceptions.VariableNotExistStackError as e:
            raise exceptions.DunderUnimplemented(e.var, left_ins)


class StubTreeRewriter(TreeRewriter):
    """parse the stub file (.pyi)
    added related stub file syntax (e.g. @overload, @property, if sys.version etc..
    Assumption:
        python version related stub must be declared as:
            if sys.version_info >= (3, )
        with the operand must be a tuple constant
    """

    def __init__(self, parser_mod=ast, py2=False, py2_version_check=False):
        super(StubTreeRewriter, self).__init__(parser_mod, py2)
        self.py2_version_check = py2_version_check

    def visit_functiondef(self, node: nodes.FunctionDef, parent: nodes.BaseNode):
        scope_local = parent.scope().locals
        n = super(StubTreeRewriter, self).visit_functiondef(node, parent)
        # check if it's overloaded
        for dec in n.decorator_list:
            if str(dec) == "overload":
                # insert the overloaded function. Create OverloadedFunc if it's not
                if n.name in scope_local:
                    overloaded_func = scope_local[n.name]
                    if not isinstance(overloaded_func, nodes.OverloadedFunc):
                        raise exceptions.OperationIncompatible("stubs @overload", n)
                    overloaded_func.elts.append(n)
                else:
                    overloaded_func = super(StubTreeRewriter, self).visit_overloadedfunc(n, parent)
                    scope_local[n.name] = overloaded_func
                return overloaded_func
        n.parent.scope().locals[n.name] = n
        return n

    def visit_classdef(self, node, parent):
        n = super(StubTreeRewriter, self).visit_classdef(node, parent)
        p_scope = n.parent.scope()
        p_scope.locals[n.name] = n
        # also solve for simple inheritance.
        for base in n.bases:
            cdef = p_scope.locals.get(str(base))
            if isinstance(cdef, nodes.ClassDef):
                n.locals = {**cdef.locals, **n.locals}
        return n

    def visit_if(self, node, parent):
        """parse the `if sys.version`"""
        n = nodes.If(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.test = self.visit(node.test, n)
        if isinstance(n.test, nodes.Compare) and str(n.test.left) == "sys.version_info":
            if len(n.test.comparators) == 1:
                py_version = (2, 7) if self.py2_version_check else (3, 6)
                # substitute sys.version_info
                meth = COMP_METHOD[n.test.ops[0]]
                if meth(py_version, tuple([el.value for el in n.test.comparators[0].elts])):
                    n.body = [self.visit(body, n) for body in node.body]
                else:
                    n.orelse = [self.visit(orelse, n) for orelse in node.orelse]
                return n
        n.body = [self.visit(body, n) for body in node.body]
        n.orelse = [self.visit(orelse, n) for orelse in node.orelse]
        return n

    def visit_annassign(self, node, parent):
        """insert the typestub into the locals. Doesn't support Attribute annotate"""
        n = super(StubTreeRewriter, self).visit_annassign(node, parent)
        if node.simple == 1:
            type_stub = nodes.TypeStub(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
            type_stub.postinit(n.annotation, n.value)
            n.scope().locals[str(n.target)] = type_stub
        return n
