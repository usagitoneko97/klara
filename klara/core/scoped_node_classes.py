import ast
from collections import deque

from . import exceptions
from .bases import BaseNode, LocalsDictNode, Proxy
from .decorators import cachedproperty
from .node_classes import Arg, Assign, AssignName, Expr, List, MultiLineBlock, Sequence, Statement, Variable
from .ssa_visitors import VariableGetter


def _c3_merge(sequences):
    """Merges MROs in *sequences* to a single MRO using the C3 algorithm.
    Adapted from http://www.python.org/download/releases/2.3/mro/.
    """
    result = []
    while True:
        sequences = [s for s in sequences if s]  # purge empty sequences
        if not sequences:
            return result
        for s1 in sequences:  # find merge candidates among seq heads
            candidate = s1[0]
            for s2 in sequences:
                if candidate in s2[1:]:
                    candidate = None
                    break  # reject the current head, it appears later
            else:
                break
        if not candidate:
            # Show all the remaining bases, which were considered as
            # candidates for the next mro sequence.
            raise exceptions.InconsistentMroError("Cannot create a consistent method resolution order ")

        result.append(candidate)
        # remove the chosen candidate
        for seq in sequences:
            if seq[0] == candidate:
                del seq[0]
    return None


def clean_duplicates_mro(sequences):
    for sequence in sequences:
        # FIXME: use class qualified name (with the correct scope) instead of just node.name
        names = [(node.lineno, node.name) if node.name else None for node in sequence]
        last_index = dict(map(reversed, enumerate(names)))
        if names and names[0] is not None and last_index[names[0]] != 0:
            raise exceptions.DuplicateBasesError("Duplicates found in MRO")
        yield [node for i, (node, name) in enumerate(zip(sequence, names)) if name is None or last_index[name] == i]


class ScopeSsaMixin:
    def generate_ssa_func(self):
        """generate multiple statement to simulate renaming of Scope without body.
        1. generate Name object for scope name.
        create stmt:
            Assign: {self.func} = Proxy(self)
        :return: tuple of statement
        """
        stmt = Assign(parent=self.parent)
        stmt.postinit(targets=[AssignName.quick_build(self.name, parent=stmt)], value=Proxy(self))
        return (stmt,)


class Module(LocalsDictNode, MultiLineBlock):
    """Class representing ast.Module"""

    body = []
    name = ""
    path = None

    _fields = ("body",)
    _other_fields = ("name", "path")

    def __init__(self, name="", path=None):
        """"""
        super(Module, self).__init__()
        self.name = name
        self.path = path

    def __repr__(self):
        return "Module {}".format(self.name).strip()

    def postinit(self, body=None):
        self.body = body or []

    def get_statements(self):
        for body in self.body:
            yield from body.get_statements()


class FunctionMixin:
    def mock_args(self, offset=0):
        """
        insert a statement with targets=all the argument starting with offset. Mainly for renaming
        :param offset: The offset of arg to apply
        :return: None
        """
        init_var_version = {}
        init_counter = {}
        # FIXME: temporary add statement stub to represent argument
        for arg in self.args.args[offset:]:
            init_var_version[arg.arg] = deque((0,))
            init_counter[arg.arg] = 1
            stmt = Assign(parent=self)
            name = AssignName.quick_build(arg.arg, ctx=ast.Store(), parent=stmt, version=0)
            stmt.postinit(targets=[name], value=arg)
            self.locals[repr(name)] = stmt.value
        self.ssa_record.merge(init_counter, init_var_version)

    def init_class_methods(self):
        """necessary initialization involving method.
        This will setup the `self` argument to contain the class available attribute.
        """
        self.mock_args()


class FunctionDef(LocalsDictNode, MultiLineBlock, Statement, ScopeSsaMixin, FunctionMixin):
    _fields = ("name", "args", "body", "decorator_list", "returns")
    _other_fields = ("lineno", "col_offset", "parent", "return_nodes", "called_by")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(FunctionDef, self).__init__(lineno, col_offset, parent)
        self.return_nodes = []
        self.called_by = []

    def __repr__(self):
        return "Function {} in scope {}".format(self.name, self.parent)

    def postinit(self, name, args, body, decorator_list, returns):
        self.name = name
        self.args = args
        self.body = body
        self.decorator_list = decorator_list
        self.returns = returns

    def get_statements(self):
        for body in self.body:
            yield from body.get_statements()

    def is_constructor(self):
        return self.name == "__init__" and self.type == "method"

    def get_arg_instance(self, arg_number):
        """get the instance for arg
        This can be use to check the instance modify in this scope. E.g.:
        >>> from klara.tools.tree_rewriter import AstBuilder
        >>> tree = AstBuilder().string_build("def __init__(self): self.x = 1")
        >>> tree.body[0].get_arg_instance(0)
        `self` instance being added attribute of `x`. Can merge it back to the instance
        :param arg_number: the position of argument to
        :return:
        """
        try:
            arg = self.args.args[arg_number]
            ins = self.instance_dict.get(arg)
            if not ins:
                raise ValueError("arg: {} does not exist in instance dict".format(arg))
            return ins
        except IndexError:
            raise ValueError("arg number: {} exceed the argument length".format(arg_number))

    @cachedproperty
    def type(self):
        """return the function type for this node
        Possibles values are method, function, staticmethod and classmethod.
        Doesn't handle decorator resolving yet. Only statically check the functionDef itself.
        """
        descriptor = {"staticmethod", "classmethod"}
        if isinstance(self.parent.scope(), ClassDef):
            for dec in self.decorator_list:
                if str(dec) in descriptor:
                    return str(dec)
            return "method"
        else:
            return "function"

    def is_property(self):
        if len(self.decorator_list) > 0:
            n = self.decorator_list[-1]
            # only check for builtin property,
            # there are other property object e.g. cached property
            if str(n) == "property":
                return True
        return False

    def assign_instance(self, value: Arg, class_instance, duplicate_ins=False):
        """point the arg to the class_instance during inference stage.
        if duplicate_ins is True, the class_instance will be duplicated, this means
        that any attribute that assigned to the instance will not affect the original
        class instance.
        :param value: the argument
        :param class_instance: class instance to point to
        :param duplicate_ins: boolean for duplicating class instance
        :return: None
        """
        stmt = Assign(parent=self)
        name = AssignName.quick_build(id=value.arg, ctx=ast.Store(), parent=stmt, version=0)
        stmt.postinit(targets=[name], value=value)
        if duplicate_ins:
            class_instance = LocalsDictNode.from_other_instance(class_instance)
        self.instance_dict[value] = class_instance
        self.locals[repr(name)] = stmt.value

    def generate_ssa_decorator(self):
        """generate an expression to rename all the decorators
        create stmt:
            Expr: decorators
        :return: Expr
        """
        return Expr.quick_build(parent=self.parent, value=List.quick_build(elts=self.decorator_list))

    def generate_ssa_func(self):
        """generate multiple statement to simulate renaming of Scope without body.
        1. generate Name object for scope name.
        2. collect all Name object to be rename except body.
        create stmt:
            Assign: {self.func} = Proxy(self)
            Expr: {list of collected name}
        :return: tuple of statement
        """
        (stmt,) = super(FunctionDef, self).generate_ssa_func()
        arg_vg = VariableGetter.get_variable(self.args).values
        return_vg = []
        if self.returns:
            return_vg = VariableGetter.get_variable(self.returns).values
        collected_name = arg_vg + return_vg
        if len(collected_name) > 0:
            expr = Expr(parent=self.parent)
            elts = List(parent=expr)
            elts.postinit(elts=collected_name)
            expr.postinit(value=elts)
            return stmt, expr
        return (stmt,)

    def get_return_type(self):
        """E.g. def foo(a: int) will return the type int
        Raise:"""
        if not isinstance(self.returns, Variable):
            raise exceptions.UnannotatedError(self.returns)
        # quick hack to check only for built-in type (int, str etc...)
        if self.returns.is_built_in_type():
            return self.returns.get_built_in_type()
        else:
            return type(None)

    def init_class_methods(self):
        """necessary initialization involving method.
        This will setup the `self` argument to contain the class available attribute.
        """
        if self.type == "method":
            self_arg = self.args.args[0]
            self.ssa_record.var_version_list[self_arg.arg] = deque((0,))
            self.ssa_record.counter[self_arg.arg] = 1
            self.assign_instance(self_arg, self.parent, duplicate_ins=True)
            self.mock_args(offset=1)
        else:
            self.mock_args()


class Lambda(LocalsDictNode, FunctionMixin):
    _fields = ("args", "body")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Lambda, self).__init__(lineno, col_offset, parent)

    def postinit(self, args, body):
        self.args = args
        self.body = body

    def _infer(self, context, inferred_attr=None):
        yield from self.body.infer(context)


class ClassDef(LocalsDictNode, MultiLineBlock, ScopeSsaMixin):
    _fields = ("name", "bases", "keywords", "starargs", "kwargs", "body", "decorator_list")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(ClassDef, self).__init__(lineno, col_offset, parent)

    def __repr__(self):
        return 'Class "{}" in scope {}'.format(self.name, self.parent)

    def postinit(self, name, bases, keywords=None, starargs=None, kwargs=None, body=None, decorator_list=None):
        self.name = name
        self.bases = bases
        self.keywords = keywords or []
        self.starargs = starargs
        self.kwargs = kwargs
        self.body = body or []
        self.decorator_list = decorator_list or []

    def get_statements(self):
        for body in self.body:
            yield from body.get_statements()

    def get_constructor(self):
        cons = self.get_latest_stmt("__init__")
        if isinstance(cons, FunctionDef) or (type(cons) is Proxy and isinstance(cons.obj, FunctionDef)):
            return cons
        raise exceptions.VariableNotExistStackError(self)

    def resolve_instance(self):
        """no need to resolve since it's class"""
        pass

    def is_inherited_by(self, base):
        return base in [str(b) for b in self.bases]

    def generate_ssa_func(self):
        (stmt,) = super(ClassDef, self).generate_ssa_func()
        values = []
        for b in self.bases:
            b_v = VariableGetter.get_variable(b).values
            values.extend(b_v)
        if values:
            expr = Expr(parent=self.parent)
            elts = List(parent=expr)
            elts.postinit(elts=values)
            expr.postinit(value=elts)
            return stmt, expr
        return (stmt,)

    def _inferred_bases(self, context=None):
        for base in self.bases:
            try:
                inherited_cls_res = next(base.infer(context))
                if inherited_cls_res.status:
                    yield inherited_cls_res.result
            except StopIteration:
                pass

    def _compute_mro(self, context=None):
        inferred_bases = list(self._inferred_bases(context=context))
        bases_mro = []
        for base in inferred_bases:
            if base is self:
                continue

            try:
                mro = base._compute_mro(context=context)
                bases_mro.append(mro)
            except NotImplementedError:
                # Some classes have in their ancestors both newstyle and
                # old style classes. For these we can't retrieve the .mro,
                # although in Python it's possible, since the class we are
                # currently working is in fact new style.
                # So, we fallback to ancestors here.
                ancestors = list(base.ancestors(context=context))
                bases_mro.append(ancestors)

        unmerged_mro = [[self]] + bases_mro + [inferred_bases]
        unmerged_mro = list(clean_duplicates_mro(unmerged_mro))
        return _c3_merge(unmerged_mro)


class Yield(BaseNode):
    """Yield is an expression , must be wrapped with expr"""

    _fields = ("value",)
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(Yield, self).__init__(lineno, col_offset, parent)

    def postinit(self, value):
        self.value = value


class YieldFrom(Yield):
    pass


class GeneratorExp(LocalsDictNode):
    _fields = ("elt", "generators")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(GeneratorExp, self).__init__(lineno, col_offset, parent)

    def postinit(self, elt, generators):
        self.elt = elt
        self.generators = generators


class DictComp(LocalsDictNode):
    _fields = ("key", "value", "generators")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(DictComp, self).__init__(lineno, col_offset, parent)

    def postinit(self, key, value, generators):
        self.key = key
        self.value = value
        self.generators = generators


class ListComp(LocalsDictNode):
    _fields = ("elt", "generators")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(ListComp, self).__init__(lineno, col_offset, parent)

    def postinit(self, elt, generators):
        self.elt = elt
        self.generators = generators


class SetComp(LocalsDictNode):
    _fields = ("elt", "generators")
    _other_fields = ("lineno", "col_offset", "parent")

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(SetComp, self).__init__(lineno, col_offset, parent)

    def postinit(self, elt, generators):
        self.elt = elt
        self.generators = generators


class OverloadedFunc(Sequence):
    """Class that represents @overload decorated FunctionDef.
    Contains list of overloaded function"""

    def __init__(self, lineno, col_offset, parent, first_func):
        super(OverloadedFunc, self).__init__(lineno, col_offset, parent, [first_func])
        self.name = first_func.name

    def get_return_type(self, *args, context):
        for func in self.elts:
            # continue to map until it matches
            if context.map_args_to_func(*args, func_node=func, remove_default=False):
                yield from func.infer_return_value(context)
