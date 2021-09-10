import abc
import ast as ast_mod
import copy
from functools import lru_cache
from typing import List as L, Union

from . import base_manager, exceptions, utilities
from .bases import BaseContainer, BaseInstance, BaseNode, LocalsDictNode, MultiLineBlock, Sequence

BASE_MANAGER = base_manager.BaseManager()


class InvertCondMixin:
    @lru_cache(maxsize=None)
    def invert_condition(self: BaseNode):
        """Invert the condition of this node.
        wrap the node in `not()`
        """
        uo = UnaryOp(self.lineno, self.col_offset, self.parent)
        uo.postinit(op="not", operand=self)
        return uo

    def wrap_bool(self):
        bool_node = Bool(self.lineno, self.col_offset, self.parent)
        bool_node.postinit(self)
        return bool_node


class Statement(BaseNode):
    """Node representing statement"""

    _other_fields = ("is_phi", "replaced_links")

    def __init__(self, lineno=None, col_offset=None, parent=None, is_phi=False, replaced_links=None):
        super(Statement, self).__init__(lineno, col_offset, parent)
        # store variable that is replacing current variable. Useful in determining bound conditions
        # when there are variable replacing current.
        self.replaced_links = replaced_links or []
        self.is_phi = is_phi

    def get_statements(self):
        yield self

    def statement(self):
        return self

    def get_call_node(self):
        """To be implemented in Assign and Expr"""

    def get_targets(self):
        """To be implemented in Assign and AugAssign.
        Return the targets variable
        """
        return ()

    def get_values(self):
        """To be implemented in Assign and AugAssign"""

    def get_all_replaced_links(self):
        """Get all replaced links' statement, traversing the links"""
        for replaced_value in self.replaced_links:
            yield replaced_value
            stmt = replaced_value.statement()
            yield from stmt.get_all_replaced_links()

    def _get_value_from_opposite_assignment(self, value, value_container, target_container, allow_subscript=False):
        """Get the `value` that is stored in `value_container` in the `target_container`
        also help to unpack the value. It follows the steps below:
        1. get the real slice value from the relationship of `value` in `value_container`
        2. if the target is Container, use the real slice with the element of the container
        3. if the target is a variable, construct a slice obj
        Raise: ValueError if there's error in unpacking, or structural error
        """
        if isinstance(value_container, Sequence):
            try:
                slices = self._get_real_slice_from_var(value, value_container)
                result = target_container
                for actual_slice in slices:
                    if isinstance(result, BaseContainer):
                        result = result.get_actual_container()[actual_slice]
                    else:
                        if allow_subscript:
                            subscript_var = Subscript(target_container.lineno, parent=target_container.parent)
                            slice_node = built_slice_node(self.lineno, parent=subscript_var, value=actual_slice)
                            subscript_var.postinit(value=result, slice=slice_node, ctx=Load())
                            result = subscript_var
                return result
            except ValueError:
                # search in other targets
                pass
            except IndexError:
                raise ValueError(
                    "not enough values to unpack, variable: {} exceed value: {})".format(value, target_container)
                )
        else:
            # not a container, there's no need to unpack
            return target_container
        raise ValueError("variable: {} does not exist in targets: {}".format(value, value_container))

    @staticmethod
    def _get_real_slice_from_var(var, container):
        """
        construct a real slice() object based on the relationship of var in container
        :param var: variable refer to construct the slice
        :param container: the container that contain variable var
        :return: a slice() object
        """
        index, elem = container.get_index(var)
        # replace var with the value in the container. Example of that is when the var is starred.
        slice_nodes = []
        for i in index[:-1]:
            slice_nodes.append(i)
            container = container.elts[i]
        if isinstance(elem, Starred):
            lower = index[-1] or None
            upper = -(len(container.elts) - index[-1] - 1) or None
            slice_nodes.append(slice(lower, upper))
        else:
            slice_nodes.append(index[-1])
        return slice_nodes

    def get_rhs_value(self, var=None):
        """get variable in rhs that is associate with var in lhs
        E.g.
        a, b, c = d ,e, f = g, h, i
        calling `get_rhs_value(b)` will return h
        :param var: the variable in the targets
        :return: Variable in rhs
        """
        for target in self.get_targets():
            try:
                val = self._get_value_from_opposite_assignment(var, target, self.get_values(), allow_subscript=True)
                return val
            except ValueError:
                continue
        raise ValueError("variable: {} does not exist in targets: {}".format(var, self.get_values()))

    def get_lhs_value(self, var):
        """get targets variable that is associated with rhs variable var
        E.g.
        a.b = c.d = d
        calling get_lhs_value(d) will return [a.b, c.d]
        a.b, e.f, f.g = c.d, d.e, g = d, e, f
        calling get_lhs_value(f) will return [f.g, d.e]
        :param var: the variable in rhs
        :return: list of targets associated with the var
        """
        vals = []
        for target in self.get_targets():
            try:
                val = self._get_value_from_opposite_assignment(var, self.get_values(), target, allow_subscript=False)
                vals.append(val)
            except ValueError:
                pass
        return vals


class Assign(Statement):
    _fields = ("targets", "value")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Assign, self).__init__(lineno, col_offset, parent)

    def __repr__(self):
        def format_targets():
            return repr(tuple(self.targets))

        return "Assign: {} = {}".format(format_targets(), repr(self.value))

    def postinit(self, targets, value):
        self.is_phi = isinstance(value, Phi)
        self.targets = targets
        self.value = value

    def get_targets(self):
        return self.targets

    def get_values(self):
        return self.value


class AugAssign(Statement):
    _fields = ("target", "op", "value")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(AugAssign, self).__init__(lineno, col_offset, parent)

    def postinit(self, target, op, value):
        self.target = target
        self.op = op
        self.value = value

    def get_targets(self):
        return [self.target]

    def get_values(self):
        """Use the whole node as value in locals"""
        return self


class AnnAssign(Statement):
    _fields = ("target", "annotation", "value", "simple")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(AnnAssign, self).__init__(lineno, col_offset, parent)

    def postinit(self, target, annotation, value, simple):
        self.target = target
        self.annotation = annotation
        self.value = value
        self.simple = simple


class Variable(BaseNode, abc.ABC, InvertCondMixin):
    """mixin for variable related"""

    def __init__(self, lineno=None, col_offset=None, parent=None, links=None, version=-1):
        self.links = links
        self.version = version
        super(Variable, self).__init__(lineno, col_offset, parent)

    @staticmethod
    def build_var(vars: tuple, assigned=False, lineno=None, col_offset=None, parent=None, links=None, version=-1):
        """build Variable class based on the tuple.
        E.g.
        vars=(a, b, c) will return Attribute: (a.b.c)
        """
        first_name_cls = AssignName if (assigned is True) and (len(vars) <= 1) else Name
        last_attr_cls = AssignAttribute if assigned is True else Attribute
        name = (
            first_name_cls.quick_build(
                vars[0], lineno=lineno, col_offset=col_offset, parent=parent, links=links, version=version
            )
            if isinstance(vars[0], str)
            else vars[0]
        )
        prev = name
        attr_obj = name
        for attr in vars[1:-1]:
            attr_obj = Attribute.quick_build(
                prev, attr, lineno=lineno, col_offset=col_offset, parent=parent, links=links, version=version
            )
            prev = attr_obj
        if len(vars) > 1:
            last_attr = last_attr_cls.quick_build(
                attr_obj, vars[-1], lineno=lineno, col_offset=col_offset, parent=parent, links=links, version=version
            )
        else:
            last_attr = attr_obj
        return last_attr

    @abc.abstractmethod
    def get_var_repr(self):
        """get the str representation of current node.
        The difference between this and __repr__ is at nodes.Attribute,
        this method will return the attr with the version, not the whole str
        """

    @abc.abstractmethod
    def is_built_in_type(self):
        """check whether the name represents built in type.
        Return True when self.id / self.attr represents python built-in type. E.g. int, str etc...
        """

    @abc.abstractmethod
    def get_built_in_type(self):
        """get the built in type class e.g. int, str of this variable representing"""

    @abc.abstractmethod
    def get_base_var(self):
        """get the base variable string without ssa version"""

    def is_load_var(self):
        """checking the 'ctx' if it's available"""
        return hasattr(self, "ctx") and isinstance(self.ctx, Load)


BUILT_IN_TYPE = (
    "int",
    "str",
    "AnyStr",
    "bool",
    "float",
    "complex",
    "unicode",
    "basestring",
    "list",
    "tuple",
    "xrange",
    "dict",
    "set",
    "frozenset",
    "type",
    "object",
    "file",
)
BUILT_IN_TYPE_MAP = {
    "int": int,
    "str": str,
    "bool": bool,
    "float": float,
    "list": list,
    "tuple": tuple,
    "set": set,
    "AnyStr": str,
}


class Name(Variable):
    """Class represents name (variable) that have ssa attributes (version) and use-def chains"""

    _fields = ("id", "ctx")  # preserved ctx even though it's not necessary for compatibility issues
    # links represent use-def chain links
    _other_fields = ("lineno", "col_offset", "parent", "links")

    def __init__(self, lineno=None, col_offset=None, parent=None, links=None, version=-1):
        super(Name, self).__init__(lineno, col_offset, parent, links, version)

    def __repr__(self):
        return "{}_{}".format(self.id, self.version) if self.version >= 0 else str(self.id)

    def __str__(self):
        return str(self.id)

    def get_var_repr(self):
        return self.__repr__()

    def get_base_var(self):
        return self.id

    def separate_members(self):
        """return a tuple that contain name for each attribute.
        E.g.
        a.b.c -> ('a', 'b', 'c')
        """
        return (self.id,)

    def postinit(self, id, ctx=None):
        self.id = id
        self.ctx = ctx

    @classmethod
    def quick_build(cls, id, ctx=None, lineno=None, col_offset=None, parent=None, links=None, version=-1):
        c = cls(lineno, col_offset, parent, links, version)
        c.postinit(id, ctx)
        return c

    @classmethod
    def quick_build_from_counter_part(cls, var):
        """build this class using counterpart (Name -> AssignName)"""
        c = cls(var.lineno, var.col_offset, var.parent)
        c.postinit(var.id, var.ctx)
        return c

    def is_name_constant(self):
        # Python 2 treat name constant as nodes.Name
        if self.id in ("True", "None", "False"):
            return True
        return False

    def convert_to_ssa(self):
        """fill the version based on instance()"""
        if not self.is_name_constant() and self.version == -1:
            ins = self.instance()
            if ins:
                ver = ins.get_version(self.id)
                BASE_MANAGER.logger.debug("SSA", "converting variable: '{}' to version: {}", self, ver)
                self.version = ver

    def is_built_in_type(self):
        return self.id in BUILT_IN_TYPE

    def get_built_in_type(self):
        return BUILT_IN_TYPE_MAP.get(self.id)


class AssignName(Name):
    """class represents name that are being assigned to in Assign statement"""

    _fields = ("id", "ctx")  # preserved ctx even though it's not necessary for compatibility issues
    # links represent def-use chain links
    _other_fields = ("lineno", "col_offset", "parent", "links")

    def __init__(self, lineno=None, col_offset=None, parent=None, links=None, version=-1):
        super(AssignName, self).__init__(lineno, col_offset, parent, links, version)

    def convert_to_ssa(self):
        """update and fill the version, fill the locals dict"""
        if not self.is_name_constant() and self.version == -1:
            BASE_MANAGER.logger.debug(
                "SSA", "converting variable: '{}' in line {} to version: {}".format(self, self.lineno, self.version)
            )
            ins = self.instance()
            try:
                field = ins.get_latest_stmt_from_stack(self.id)
                stmt = field.statement()
                if hasattr(stmt, "replaced_links"):
                    stmt.replaced_links.append(self)
            except exceptions.VariableNotExistStackError:
                pass
            self.version = ins.update_version(self.id)
            try:
                self.instance().locals[self.get_var_repr()] = self.statement().get_rhs_value(self)
            except ValueError:
                pass


class DelName(Name):
    """class for representing `del var`"""


class Attribute(Variable):
    _fields = ("value", "attr", "ctx")
    _other_fields = ("lineno", "col_offset", "parent", "links")

    def __init__(self, lineno=None, col_offset=None, parent=None, links=None, version=-1):
        self.links = links
        self.version = version
        super(Attribute, self).__init__(lineno, col_offset, parent)

    @classmethod
    def quick_build(cls, value, attr, ctx=None, lineno=None, col_offset=None, parent=None, links=None, version=-1):
        c = cls(lineno, col_offset, parent, links, version)
        c.postinit(value, attr, ctx)
        return c

    @classmethod
    def quick_build_from_counter_part(cls, var):
        """build this class using counterpart (Name -> AssignName)"""
        c = cls(var.lineno, var.col_offset, var.parent)
        value = copy.copy(var.value)
        value.parent = c
        c.postinit(value, var.attr, var.ctx)
        return c

    def __repr__(self):
        return "{}.{}".format(repr(self.value), self.get_var_repr())

    def __str__(self):
        return "{}.{}".format(str(self.value), self.attr)

    def separate_members(self):
        """return a tuple that contain name for each attribute.
        E.g.
        a.b.c -> ('a', 'b', 'c')
        """
        return self.value.separate_members() + (self.attr,)

    def get_var_repr(self):
        return "{}_{}".format(self.attr, self.version) if self.version >= 0 else self.attr

    def get_base_var(self):
        return self.attr

    def postinit(self, value, attr, ctx):
        self.value = value
        self.attr = attr
        self.ctx = ctx

    def is_name_constant(self):
        if self.attr in ("True", "None", "False"):
            return True
        return False

    def get_value_from_locals(self):
        try:
            val = self.value.instance().locals.get(self.value.get_var_repr())
            if val:
                return val
        except exceptions.InstanceNotExistError:
            return None

    def convert_to_ssa(self):
        """fill the version based on instance()
        convert_to_ssa will create new instance if it's not found. The overall process is as follow:
            - if it's in locals (e.g. it's arg), create an instance with the arg object as the key in
              instance_dict. (no modifying of locals is necessary)
            - if it's not in locals (e.g. for the case of self.a.b), create UselessStub for the purpose
              of placing it in locals, and the UselessStub obj will use as key to instance_dict that point
              to also a newly created instance.
        """
        if not self.is_name_constant() and self.version == -1:
            try:
                ins = self.instance()
                ins.resolve_instance()
            except exceptions.InstanceNotExistError:
                arg = self.get_value_from_locals()
                ins = LocalsDictNode()
                if isinstance(arg, (Arg, Import)):
                    self.scope().instance_dict[arg] = ins
            except exceptions.NotInLocalsError as e:
                ins, _ = self.handle_unresolved_attr(e.scope, e.var)
            except (NotImplementedError, AttributeError):
                return
            self.version = ins.get_version(self.attr)
            BASE_MANAGER.logger.debug(
                "SSA", "converting variable: '{}' in line {} to version: {}", self, self.lineno, self.version
            )

    def handle_unresolved_attr(self, scope, var):
        """generate ssa stmt that act as a stub.
         when the attribute does not exist, a statement will be created to
         signal during infer stage that this attribute does not exist.
         Also will add TempObj in the instance_dict since it's a temporary instance
         create:
            Assign: self.value = TempObj()
        :return:
        """
        stmt = Assign(parent=self.scope())
        temp_obj = TempInstance(parent=stmt)
        stmt.postinit(targets=[self.value], value=temp_obj)
        ins = LocalsDictNode()
        scope.locals[var] = temp_obj
        scope.instance_dict[temp_obj] = ins
        return ins, temp_obj

    def is_built_in_type(self):
        # TODO: Handle types.XXX in the future
        return False

    def get_built_in_type(self):
        return type(None)


class AssignAttribute(Attribute):
    _fields = ("value", "attr", "ctx")
    _other_fields = ("lineno", "col_offset", "parent", "links")

    def postinit(self, value, attr, ctx):
        self.value = value
        self.attr = attr
        self.ctx = ctx

    def convert_to_ssa(self):
        """update and fill the version, fill the locals dict"""
        if not self.is_name_constant() and self.version == -1:
            local_val = self.get_value_from_locals()
            try:
                ins = self.instance()
                ins.resolve_instance()
            except exceptions.InstanceNotExistError:
                # create a new scope. See (#rja0j)
                ins = LocalsDictNode()
                if isinstance(local_val, (Arg, Import, ImportFrom)):
                    self.scope().instance_dict[local_val] = ins
            except exceptions.NotInLocalsError as e:
                ins, local_val = self.handle_unresolved_attr(e.scope, e.var)
            except AttributeError:
                return
            # because it's AssignAttribute, it should include in the global_var
            if isinstance(local_val, (Arg, TempInstance)):
                self.scope().global_var[self.separate_members()] = ins
            try:
                field = ins.get_latest_stmt_from_stack(self.attr)
                stmt = field.statement()
                if hasattr(stmt, "replaced_links"):
                    stmt.replaced_links.append(self)
            except exceptions.VariableNotExistStackError:
                pass
            self.version = ins.update_version(self.attr)
            BASE_MANAGER.logger.debug(
                "SSA", "converting variable: {} in line {} to version: {}".format(self, self.lineno, self.version)
            )
            try:
                ins.locals[self.get_var_repr()] = self.statement().get_rhs_value(self)
            except ValueError:
                pass


class DelAttribute(Attribute):
    """class for `del ins.attr`"""


class Starred(Variable):
    _fields = ("value",)
    _other_fields = ("lineno", "col_offset", "parent", "links")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Starred, self).__init__(lineno, col_offset, parent)

    def __repr__(self):
        return "*" + repr(self.value)

    def postinit(self, value):
        self.value = value

    def get_var_repr(self):
        return repr(self.value)

    def is_built_in_type(self):
        return False

    def get_built_in_type(self):
        return type(None)

    def get_base_var(self):
        return self.value.get_base_var()


class AssignStarred(Starred):
    _fields = ("value",)
    _other_fields = ("lineno", "col_offset", "parent", "links")


class BinOp(BaseNode, InvertCondMixin):
    _fields = ("left", "right")
    _other_fields = ("op", "lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(BinOp, self).__init__(lineno, col_offset, parent)

    def __repr__(self):
        return "BinOp: {} {} {}".format(repr(self.left), self.op, repr(self.right))

    def __str__(self):
        def format_operand(operand):
            return "({})".format(str(operand)) if isinstance(operand, BinOp) else str(operand)

        return "{} {} {}".format(format_operand(self.left), self.op, format_operand(self.right))

    def postinit(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right


class Const(BaseNode, BaseInstance, InvertCondMixin):
    _fields = ("value",)

    def __init__(self, value, lineno=None, col_offset=None, parent=None):
        self.value = value
        super(Const, self).__init__(lineno, col_offset, parent)

    def __hash__(self):
        try:
            # hash the type as well since hash(0) == hash("")
            return hash((self.value, type(self.value)))
        except TypeError:
            return super(Const, self).__hash__()

    def __repr__(self):
        return repr(self.value)

    def get_type(self):
        """get the type of the constant holding"""
        return type(self.value)

    def to_ast(self):
        return ast_mod.Constant(value=self.value)


class UnaryOp(BaseNode, InvertCondMixin):
    _fields = ("op", "operand")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(UnaryOp, self).__init__(lineno, col_offset, parent)

    def __repr__(self):
        return "UnaryOp: {}({})".format(repr(self.op), repr(self.operand))

    def __str__(self):
        return "{}({})".format(str(self.op), str(self.operand))

    def postinit(self, op=None, operand=None):
        self.op = op
        self.operand = operand


class BoolOp(BaseNode, InvertCondMixin):
    _fields = ("op", "values")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(BoolOp, self).__init__(lineno, col_offset, parent)

    def __repr__(self):
        res = repr(self.values[0])
        for v in self.values[1:]:
            res += " {} {}".format(self.op, repr(v))
        return res

    def __str__(self):
        res = str(self.values[0])
        for v in self.values[1:]:
            res += " {} {}".format(self.op, v)
        return res

    def postinit(self, op, values):
        self.op = op
        self.values = values


class Phi(BaseNode):
    _fields = ("value",)
    _other_fields = ("base_name", "lineno", "col_offset", "parent", "replaced_map")

    def __init__(self, value: L[Name], base_name="", lineno=None, col_offset=None, parent=None):
        self.value = value
        self.base_name = base_name
        # to map out which variable in `value` is getting replaced in other fields in `value`
        # this is for determining valid bound conditions for each variable
        self.replaced_map = {}
        super(Phi, self).__init__(lineno, col_offset, parent)

    def __repr__(self):
        return "Phi{}".format(repr(tuple(self.value)))

    def __str__(self):
        return "Phi{}".format(str(tuple(self.value)))

    def check_exist(self, version):
        for node in self.value:
            if node.version == version:
                return True
        return False


class Call(BaseNode, InvertCondMixin):
    _fields = ("func", "args", "keywords")
    _other_fields = ("lineno", "col_offset", "parent", "ssa_records", "locals")

    def __init__(self, lineno=None, col_offset=None, parent=None, ssa_record=None, locals_=None):
        super(Call, self).__init__(lineno, col_offset, parent)
        # the ssa records up until this calling point
        self.ssa_record = ssa_record
        # locals dict up until this calling point. The purpose is to
        # preserve the locals history to avoid function body to use
        # locals that is defined after the call statement.
        # The locals will not only consist of scope().locals but all locals
        # that is relevant to the caller body. E.g.
        # >>> a_global = 1
        # >>> f.x = 1
        # >>> f.g.h() # scope().locals and f.locals need to stored and parsed to the body.
        # mapping: "instance" -> locals for the instance
        #          "scope"    -> locals for the scope
        self.locals = locals_ or {}

    def __repr__(self):
        return "Call: {}({})".format(repr(self.func), tuple(self.args))

    def __str__(self):
        return "{}({})".format(str(self.func), tuple(self.args))

    def get_var_repr(self):
        return repr(self.func)

    def postinit(self, func=None, args=None, keywords=None):
        self.func = func
        self.args = args
        self.keywords = keywords

    def get_target_func(self):
        """return the func/method that is calling. None if it can't resolved"""
        return next(self.func.infer())


class Keyword(BaseNode):
    _fields = ("arg", "value")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Keyword, self).__init__(lineno, col_offset, parent)

    def postinit(self, arg, value):
        self.arg = arg
        self.value = value


class Pass(Statement):
    """Also useless"""

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Pass, self).__init__(lineno, col_offset, parent)

    def __repr__(self):
        return "pass"


class If(MultiLineBlock, Statement):
    _fields = ("test", "body", "orelse")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(If, self).__init__(lineno, col_offset, parent)

    def get_statements(self):
        for body in self.body + self.orelse:
            yield from body.get_statements()

    def postinit(self, test=None, body=None, orelse=None):
        self.test = test
        self.body = body
        self.orelse = orelse


class IfExp(BaseNode):
    _fields = ("test", "body", "orelse")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(IfExp, self).__init__(lineno, col_offset, parent)

    def __repr__(self):
        return "{} if {} else {}".format(self.body, self.test, self.orelse)

    def postinit(self, test, body, orelse):
        self.test = test
        self.body = body
        self.orelse = orelse


class While(MultiLineBlock, Statement):
    _fields = ("test", "body", "orelse")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(While, self).__init__(lineno, col_offset, parent)

    def get_statements(self):
        for body in self.body + self.orelse:
            yield from body.get_statements()

    def postinit(self, test=None, body=None, orelse=None):
        self.test = test
        self.body = body
        self.orelse = orelse


class For(MultiLineBlock, Statement):
    _fields = ("target", "iter", "body", "orelse")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(For, self).__init__(lineno, col_offset, parent)

    def get_statements(self):
        for body in self.body + self.orelse:
            yield from body.get_statements()

    def postinit(self, target, iter, body, orelse):
        self.target = target
        self.iter = iter
        self.body = body
        self.orelse = orelse

    def generate_ssa_stmt(self):
        stmt = Assign(self.lineno, parent=self.parent)
        self.target.parent = stmt
        self.iter.parent = stmt
        for_iter = ForIter(self.lineno, parent=stmt)
        for_iter.postinit(self.iter)
        stmt.postinit(targets=[self.target], value=for_iter)
        return stmt


class ForIter(BaseNode):
    """additional node created to unify the analysis
    E.g.
    for i in z.iter(): ...
    This will roughly translate to:
    i = ForIter(value=z.iter())
    """

    _fields = ("value",)
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(ForIter, self).__init__(lineno, col_offset, parent)

    def postinit(self, value):
        self.value = value

    def __repr__(self):
        return "ForIter: {}".format(repr(self.value))


class Return(Statement):
    _fields = ("value",)

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Return, self).__init__(lineno, col_offset, parent)

    def postinit(self, value=None):
        self.value = value

    def generate_ssa_stmt(self):
        """Generate ssa return statement
        create:
            Assign: ret_val = self.value
        """
        ret_stmt = Assign(parent=self.parent, lineno=self.lineno)
        ret_val_name = AssignName(parent=ret_stmt)
        ret_val_name.postinit(id="ret_val")
        ret_stmt.postinit(targets=[ret_val_name], value=self.value)
        return ret_stmt


class Expr(Statement, InvertCondMixin):
    _fields = ("value",)

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Expr, self).__init__(lineno, col_offset, parent)

    def __repr__(self):
        return repr(self.value)

    def __str__(self):
        return str(self.value)

    def postinit(self, value=None):
        self.value = value

    @classmethod
    def quick_build(cls, lineno=None, col_offset=None, parent=None, value=None):
        c = cls(lineno, col_offset, parent)
        c.value = value
        c.value.parent = c
        return c


class NameConstant(BaseNode, InvertCondMixin):
    _fields = ("value",)

    def __init__(self, value, lineno=None, col_offset=None, parent=None):
        self.value = value
        super(NameConstant, self).__init__(lineno, col_offset, parent)

    def __repr__(self):
        return repr(self.value)

    def __str__(self):
        return str(self.value)

    def to_ast(self):
        return ast_mod.Constant(value=self.value)


class Compare(BaseNode, InvertCondMixin):
    _fields = ("left", "ops", "comparators")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Compare, self).__init__(lineno, col_offset, parent)

    def __repr__(self):
        res = repr(self.left)
        for op, operand in zip(self.ops, self.comparators):
            res += " {} {}".format(op, repr(operand))
        return res

    def __str__(self):
        res = str(self.left)
        for op, operand in zip(self.ops, self.comparators):
            res += " {} {}".format(op, str(operand))
        return res

    def postinit(self, left=None, ops=None, comparators=None):
        self.left = left
        self.ops = ops
        self.comparators = comparators


class Bool(BaseNode, InvertCondMixin):
    """
    Bool wrapper normally used when in Boolean context (e.g. the conditions in `if` stmt).
    Python implicitly called bool() on the boolean context, in the inference systems, we'll
    need to know when is the value should be use in boolean context.

    The Bool is created during rewriting of the tree.
    """

    _fields = ("value",)
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Bool, self).__init__(lineno, col_offset, parent)

    def postinit(self, value=None):
        self.value = value

    def __repr__(self):
        return repr(self.value)

    def __str__(self):
        return str(self.value)

    @classmethod
    def wrap(cls, value: BaseNode):
        c = cls(value.lineno, value.col_offset, value)
        c.postinit(value)
        return c


class Arguments(BaseNode):
    _fields = ("args", "vararg", "kwonlyargs", "kwarg", "defaults", "kw_defaults")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Arguments, self).__init__(lineno, col_offset, parent)

    def postinit(self, args, vararg, kwonlyargs, kwarg, defaults, kw_defaults):
        self.args = args
        self.vararg = vararg
        self.kwonlyargs = kwonlyargs
        self.kwarg = kwarg
        self.defaults = defaults
        self.kw_defaults = kw_defaults

    def get_default(self, arg_str):
        pos = self.get_index_of_arg(arg_str)
        def_index = pos - (len(self.args) - len(self.defaults))
        if def_index >= 0:
            return self.defaults[def_index]

    def get_index_of_arg(self, arg_str):
        for i, arg in enumerate(self.args):
            if arg.arg == arg_str:
                return i


class Arg(Variable):
    _fields = ("arg", "annotation")
    _other_fields = ("lineno", "col_offset", "parent")

    def __repr__(self):
        return "Arg: {}".format(repr(self.arg))

    def __str__(self):
        return str(self.arg)

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Arg, self).__init__(lineno, col_offset, parent)

    def postinit(self, arg, annotation):
        self.arg = arg
        self.annotation = annotation

    def get_default(self):
        if not isinstance(self.parent, Arguments):
            raise exceptions.StructureError(self, self.parent, Arguments)
        return self.parent.get_default(self.arg)

    def get_var_repr(self):
        return repr(self.arg)

    def is_built_in_type(self):
        return False

    def get_built_in_type(self):
        return type(None)

    def get_base_var(self):
        return self.arg.get_base_var()


class List(Sequence, InvertCondMixin):
    _fields = ("elts",)
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(List, self).__init__(lineno, col_offset, parent)

    def __repr__(self):
        return repr(self.elts)

    def __str__(self):
        return str(self.elts)

    def postinit(self, elts):
        self.elts = elts

    @classmethod
    def quick_build(cls, lineno=None, col_offset=None, parent=None, elts=None):
        c = cls(lineno, col_offset, parent)
        c.elts = elts
        return c

    @staticmethod
    def get_actual_type():
        return list


class Set(Sequence, InvertCondMixin):
    _fields = ("elts",)
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, elts=None, lineno=None, col_offset=None, parent=None):
        super(Set, self).__init__(elts, lineno, col_offset, parent)

    def __repr__(self):
        return repr(self.elts)

    def __str__(self):
        return str(self.elts)

    def postinit(self, elts):
        self.elts = elts

    def get_actual_container(self):
        return set(self.elts)

    @staticmethod
    def get_actual_type():
        return set


class Tuple(Sequence, InvertCondMixin):
    _fields = ("elts",)
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Tuple, self).__init__(lineno, col_offset, parent)

    def __repr__(self):
        return repr(tuple(self.elts))

    def __str__(self):
        return str(tuple(self.elts))

    def postinit(self, elts):
        self.elts = elts

    def get_actual_container(self):
        """return the actual object for this class. E.g. Set class will return set(self.elts) instead of list"""
        return tuple(self.elts)

    @staticmethod
    def get_actual_type():
        return tuple


class Dict(BaseContainer, InvertCondMixin):
    _fields = ("keys", "values")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Dict, self).__init__(lineno, col_offset, parent)

    def __len__(self):
        return len(self.values)

    def get_actual_container(self):
        result = dict()
        for key, value in zip(self.keys, self.values):
            result[key] = value
        return result

    def postinit(self, keys, values):
        self.keys = keys
        self.values = values

    @staticmethod
    def get_actual_type():
        return dict

    def get_key_index(self, index, context):
        for i, key in enumerate(self.keys):
            for val in key.infer(context):
                if utilities.compare_inferred_node(val.result, index):
                    return i


class Subscript(Variable):
    _fields = ("value", "slice", "ctx")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None, links=None, version=-1):
        super(Subscript, self).__init__(lineno, col_offset, parent, links, version)

    def __repr__(self):
        ver = "_{}".format(self.version) if self.version >= 0 else ""
        return "{}[{}]{}".format(repr(self.value), repr(self.slice), ver)

    def __str__(self):
        ver = "_{}".format(self.version) if self.version >= 0 else ""
        return "{}[{}]{}".format(str(self.value), str(self.slice), ver)

    def postinit(self, value, slice, ctx):
        self.value = value  # the variable that it's subscripted to
        self.slice = slice  # can be Index, Slice or ExtSlice
        self.ctx = ctx  # the context of variable

    def get_var_repr(self):
        return repr(self.slice)

    def get_base_var(self):
        return "{}[{}]".format(self.value, self.slice)

    def convert_to_ssa(self):
        ins = self.instance()
        if self.is_load_var():
            self.version = ins.get_version(repr(self))
        else:
            self.version = ins.update_version(repr(self))
            try:
                ins.locals[self.get_var_repr()] = self.statement().get_rhs_value(self)
            except (ValueError, AttributeError):
                pass
        BASE_MANAGER.logger.debug(
            "SSA", "converting variable: '{}' in line {} to version: {}", self, self.lineno, self.version
        )

    def is_name_constant(self):
        return False

    def get_built_in_type(self):
        return type(None)

    def is_built_in_type(self):
        return False


class Index(BaseNode):
    _fields = ("value",)
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None, value=None):
        super(Index, self).__init__(lineno, col_offset, parent)
        self.value = value

    def __repr__(self):
        return repr(self.value)

    def __str__(self):
        return str(self.value)

    def postinit(self, value=None):
        self.value = value

    @classmethod
    def from_int(cls, lineno=None, col_offset=None, parent=None, value=None):
        c = cls(lineno, col_offset, parent)
        val = Const(value) if value is not None else None
        c.postinit(val)
        return c


class Slice(BaseNode):
    _fields = ("lower", "upper", "step")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Slice, self).__init__(lineno, col_offset, parent)

    def __repr__(self):
        lower = self.lower or ""
        upper = self.upper or ""
        step = self.step if repr(self.step) != "1" else ""
        return "{}:{}:{}".format(repr(lower), repr(upper), repr(step))

    def __str__(self):
        lower = self.lower or ""
        upper = self.upper or ""
        step = self.step if str(self.step) != "1" else ""
        return "{}:{}:{}".format(lower, upper, step)

    def __hash__(self):
        return hash((self.lower, self.upper, self.step))

    def postinit(self, lower, upper, step=None):
        self.lower = lower
        self.upper = upper
        self.step = step or Const(1)

    @classmethod
    def from_slice(cls, lineno=None, col_offset=None, parent=None, slice_node: slice = None):
        c = cls(lineno, col_offset, parent)
        start = Const(slice_node.start) if slice_node.start else None
        stop = Const(slice_node.stop) if slice_node.stop else None
        c.postinit(start, stop, slice_node.step)
        return c


def built_slice_node(lineno=None, col_offset=None, parent=None, value=None):
    """build either Slice() or Index() depending on value"""
    if isinstance(value, slice):
        constructor = Slice.from_slice
        Slice.from_slice(lineno, col_offset, parent, value)
    elif isinstance(value, int):
        constructor = Index.from_int
    else:
        raise ValueError("can't convert value: {} to slice/index node for subscript".format(value))
    return constructor(lineno, col_offset, parent, value)


class ExtSlice(BaseNode):
    _fields = ("dims",)
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(ExtSlice, self).__init__(lineno, col_offset, parent)

    def postinit(self, dims):
        self.dims = dims


class Store(BaseNode):
    _fields = tuple()
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Store, self).__init__(lineno, col_offset, parent)


class Load(BaseNode):
    _fields = tuple()
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Load, self).__init__(lineno, col_offset, parent)


class Del(BaseNode):
    _fields = ("targets",)
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Del, self).__init__(lineno, col_offset, parent)

    def postinit(self, targets):
        self.targets = targets


class Global(Statement):
    _fields = ("names",)
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Global, self).__init__(lineno, col_offset, parent)

    def postinit(self, names):
        self.names = names


class Alias(Variable):
    _fields = ("name", "asname")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None, links=None, version=-1):
        super(Alias, self).__init__(lineno, col_offset, parent, links, version)

    def __repr__(self):
        ver = ("_" + repr(self.version)) if self.version != -1 else ""
        if self.asname:
            name = self.name
            asname = "as " + self.asname + ver
        else:
            name = self.name + ver
            asname = ""
        return "{} {}".format(name, asname)

    def __str__(self):
        if self.asname:
            name = self.name
            asname = "as " + self.asname
        else:
            name = self.name
            asname = ""
        return "{} {}".format(name, asname)

    def postinit(self, name, asname):
        self.name = name
        self.asname = asname

    def get_base_var(self):
        return self.asname or self.name

    def get_var_repr(self):
        ver = ("_" + repr(self.version)) if self.version != -1 else ""
        name = self.asname or self.name
        return name + ver

    def get_built_in_type(self):
        return type(None)

    def is_built_in_type(self):
        return False

    def convert_to_ssa(self):
        """rename the name or asname to reflect the new name introduced"""
        if self.version == -1:
            ins = self.instance()
            name = self.asname or self.name
            self.version = ins.update_version(name)
            BASE_MANAGER.logger.debug(
                "SSA", "converting variable: '{}' in line {} to version: {}", self, self.lineno, self.version
            )
            if ins:
                ins.locals[self.get_var_repr()] = self.statement()


class Import(Statement):
    _fields = ("names",)
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Import, self).__init__(lineno, col_offset, parent)

    def __repr__(self):
        return "import " + repr(tuple(self.names))

    def __str__(self):
        return "import " + str(tuple(self.names))

    def postinit(self, names: L[Alias]):
        self.names = names


class ImportFrom(Statement):
    _fields = ("module", "names", "level")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(ImportFrom, self).__init__(lineno, col_offset, parent)

    def __repr__(self):
        return "from {} import {}".format(self.module, repr(tuple(self.names)))

    def __str__(self):
        return "from {} import {}".format(self.module, str(tuple(self.names)))

    def postinit(self, module: str, names: L[Alias], level: int):
        self.module = module
        self.names = names
        self.level = level


class Ellipsis(BaseNode):
    _fields = ()
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Ellipsis, self).__init__(lineno, col_offset, parent)

    def __repr__(self):
        return "(...)"


class Raise(Statement):
    _fields = ("exc", "cause")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Raise, self).__init__(lineno, col_offset, parent)

    def postinit(self, exc, cause):
        self.exc = exc
        self.cause = cause


class Assert(Statement):
    _fields = ("test", "msg")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Assert, self).__init__(lineno, col_offset, parent)

    def postinit(self, test, msg):
        self.test = test
        self.msg = msg


class Print(Statement):
    _fields = ("dest", "values", "nl")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Print, self).__init__(lineno, col_offset, parent)

    def postinit(self, dest, values, nl):
        self.dest = dest
        self.values = values
        self.nl = nl


class Delete(Statement):
    _fields = ("targets",)
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Delete, self).__init__(lineno, col_offset, parent)

    def postinit(self, targets):
        self.targets = targets


class KillVarCall(BaseNode):
    """Used for indicating killed var in a call to func/method
    e.g.
    def foo():
        global a
        a = 4
    a = 5
    foo()   # foo() will kill `a`, therefore wrap the call to foo() with KillVarCall, and add `a` into
              the vars to indicate it's killing it.
    """

    _fields = ("value", "var", "scope")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(KillVarCall, self).__init__(lineno, col_offset, parent)

    def __repr__(self):
        return "KILL {} ---> {}".format(self.var, self.value)

    def postinit(self, var: str, value: Call, scope: LocalsDictNode):
        self.var = var
        self.value = value
        self.value_scope = scope


class TempInstance(BaseNode):
    """Class that act as a temp object in locals and instance_dict interaction with non existence attribute.
    E.g.
    def foo(a):
        a.b.c = 1
        glob_var.attr = 2
    `a` is still exist in the locals since it's the argument, then we can  But `a.b` does not have locals dict
    present. That's where UselessStub help
    """

    pass


class Try(Statement):
    _fields = ("body", "handlers", "orelse", "finalbody")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Try, self).__init__(lineno, col_offset, parent)

    def postinit(self, body, handlers, orelse, finalbody):
        self.body = body
        self.handlers = handlers
        self.orelse = orelse
        self.finalbody = finalbody


class TryFinally(Statement):
    """Try blocks up to Python3.2"""

    _fields = ("body", "finalbody")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(TryFinally, self).__init__(lineno, col_offset, parent)

    def postinit(self, body, finalbody):
        self.body = body
        self.finalbody = finalbody


class TryExcept(Statement):
    """Try blocks up to Python3.2"""

    _fields = ("body", "handlers", "orelse")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(TryExcept, self).__init__(lineno, col_offset, parent)

    def postinit(self, body, handlers, orelse):
        self.body = body
        self.handlers = handlers
        self.orelse = orelse


class ExceptHandler(BaseNode):
    _fields = ("type", "name", "body")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(ExceptHandler, self).__init__(lineno, col_offset, parent)

    def postinit(self, type, name, body):
        self.type = type
        self.name = name
        self.body = body


class Break(Statement):
    _fields = ()
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Break, self).__init__(lineno, col_offset, parent)


class Continue(Statement):
    _fields = ()
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Continue, self).__init__(lineno, col_offset, parent)


class With(Statement):
    _fields = ("items", "body")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(With, self).__init__(lineno, col_offset, parent)

    def postinit(self, items, body):
        self.items = items
        self.body = body


class WithItem(BaseNode):
    _fields = ("context_expr", "optional_vars")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(WithItem, self).__init__(lineno, col_offset, parent)

    def postinit(self, context_expr, optional_vars):
        self.context_expr = context_expr
        self.optional_vars = optional_vars


class Comprehension(BaseNode):
    _fields = ("target", "iter", "ifs")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Comprehension, self).__init__(lineno, col_offset, parent)

    def postinit(self, target, iter, ifs):
        self.target = target
        self.iter = iter
        self.ifs = ifs


class TypeStub(BaseNode):
    _fields = ("type", "value")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None, _type=None, value=None):
        super(TypeStub, self).__init__(lineno, col_offset, parent)
        self._type = _type
        self.value = value

    def postinit(self, _type: Union[Name, Attribute], value):
        self.type = _type
        self.value = value
