import copy
from collections import deque

from . import exceptions


class BaseNode:
    """The base node for every newly created node"""

    _fields = ()

    def __init__(self, lineno=None, col_offset=None, parent=None, refer_to_block=None):
        self.lineno = lineno
        self.col_offset = col_offset
        self.parent = parent
        self.refer_to_block = refer_to_block
        # this will be set in MANAGER.transform to specify custom infer function for this node
        self.explicit_inference = None

    def __contains__(self, item):
        for f in self._fields:
            if getattr(self, f, None) == item:
                return True
        return False

    def generic_visit(self, visitor):
        for field, value in self.iter_fields():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, BaseNode):  # noqa: F405
                        return item.accept(visitor)
            elif isinstance(value, BaseNode):  # noqa: F405
                return value.accept(visitor)

    def accept(self, visitor):
        method = "visit_" + self.__class__.__name__.lower()
        visitor = getattr(visitor, method, self.generic_visit)
        return visitor(self)

    def get_statements(self):
        yield ()

    def scope(self):
        """return the first containing scope"""
        return self.parent.scope()

    def statement(self):
        return self.parent.statement()

    def get_children(self):
        for field in self._fields:
            attr = getattr(self, field)
            if isinstance(attr, (tuple, list)):
                yield from attr
            else:
                yield attr if attr is not None else ()

    def is_children(self, node):
        """check if the given node is part of 'self' or children"""
        if self == node:
            return True
        for c in self.get_children():
            if isinstance(c, BaseNode) and c.is_children(node):
                return True
        return False

    def iter_fields(self):
        """
        Yield a tuple of ``(fieldname, value)`` for each field in ``node._fields``
        that is present on *node*.
        """
        for field in self._fields:
            try:
                yield field, getattr(self, field)
            except AttributeError:
                pass

    def get_parent_of_type(self, type_class):
        if isinstance(self, type_class):
            return self
        return self.parent.get_parent_of_type(type_class)

    def get_target_instance(self):
        """get the assigning target instance rather than scope(). See #mr68u
        a.b.c = node
        calling node.get_target_instance() will return `a.b.c.instance()`
        """
        stmt = self.statement()
        try:
            targets = stmt.get_lhs_value(self)
            for target in targets:
                yield target.instance()
        except AttributeError:
            yield self.scope()
            return
        yield self.scope()

    def dunder_lookup(self, method):
        """try to resolve the dunder method"""
        if hasattr(self, "locals"):
            return self.locals.get(method)

    def get_stmt_target(self):
        try:
            stmt = self.statement()
            if hasattr(stmt, "targets"):
                return stmt.targets
        except AttributeError:
            return None

    def get_from_outer(self, var: str, skip: int = 0):
        """
        find the definition of `var` from outer scope recursively.
        Skip param will determine how many parent scope to skip
        :param var: variable of interest
        :param skip: how many layer of parent scope to skip
        :return:
        """
        try:
            parent_scope = self.scope()
            for _ in range(skip):
                parent_scope = parent_scope.parent.scope()
            while True:
                try:
                    # Ignore parent scope that is of type ClassDef
                    # since we assume the lookup var is looking for global
                    # name without any namespace attached.
                    if parent_scope.__class__.__name__ == "ClassDef":
                        parent_scope = parent_scope.parent.scope()
                        continue
                    return parent_scope.get_latest_stmt(var)
                except exceptions.VariableNotExistStackError:
                    parent_scope = parent_scope.parent.scope()
        except AttributeError:
            pass
        raise exceptions.VariableNotExistStackError(var)

    @staticmethod
    def get_inferred(inferred):
        if callable(inferred):
            yield from inferred()
        else:
            yield from inferred

    def prepare_inferred_value(self, inferred_attr, fields=None, context=None):
        inferred_attr = {} if inferred_attr is None else inferred_attr
        result = {}
        fields = fields or self._fields
        if isinstance(fields, str):
            fields = [fields]
        for field_str in fields:
            value = inferred_attr.get(field_str, None)
            field = getattr(self, field_str)
            if value is None:
                if isinstance(field, list):
                    value = (f.infer(context) for f in field)
                elif isinstance(field, BaseNode):
                    value = field.infer(context)
                else:
                    value = (None,)

            result[field_str] = value
        return result

    def get_bound_conditions(self):
        try:
            stmt = self.statement()
            block = stmt.refer_to_block
            bound_conditions = set()
            if block:
                bound_conditions |= block.conditions
            return bound_conditions
        except AttributeError:
            return set()


class MultiLineBlock:
    """class representing multiple line e.g. FunctionDef, ClassDef, If etc..."""

    def get_statements(self):
        for field, value in self.iter_fields():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, BaseNode):  # noqa: F405
                        yield from item.get_statements()


class Proxy:
    """Temporary holding an obj"""

    def __init__(self, obj=None):
        self.obj = obj

    def __repr__(self):
        return "Proxy to the object: {}".format(repr(self.obj))

    def __getattr__(self, item):
        if item == "obj":
            return getattr(self.__class__, "obj")
        if item in self.__dict__:
            return self.__dict__[item]
        return getattr(self.obj, item)


class BaseInstance(Proxy):
    pass


class BaseContainer(BaseNode, BaseInstance):
    """class for node that contain multiple element. E.g.: List, Set, Tuple, Dict"""

    def get_actual_container(self):
        """return the true form of the container.
        E.g. Tuple class will return tuple[self.elts]
        """

    def __str__(self):
        return str(self.get_actual_container())


class Sequence(BaseContainer):
    def __init__(self, lineno, col_offset, parent, elts=None):
        super(BaseContainer, self).__init__(lineno, col_offset, parent)
        self.elts = elts

    def __len__(self):
        return len(self.elts)

    def __hash__(self):
        return hash(tuple(self.elts))

    def __iter__(self):
        self._iter = iter(self.elts)
        return self

    def __next__(self):
        return next(self._iter)

    def get_index(self, var):
        """get the index number of var
        Also handle nested container, specifically in :
        (a, b, c), d, e = z
        """
        for n, elem in enumerate(self.elts):
            if isinstance(elem, Sequence):
                try:
                    nested_n, elem = elem.get_index(var)
                    return ((n,) + nested_n), elem
                except ValueError:
                    pass
            else:
                if elem.is_children(var):
                    return (n,), elem
        raise ValueError("{} is not in the list".format(var))

    def get_actual_container(self):
        """return the actual object for this class. E.g. Set class will return set(self.elts) instead of list"""
        return self.elts


class SsaBookKeeping(object):
    def __init__(self, counter=None, var_version_list=None):
        self.counter = counter if counter else {}
        self.var_version_list = var_version_list if var_version_list else {}
        # var_version_list at the end of the scope
        self.final_var_version = {}

    def merge(self, counter, var_version_list):
        self.counter = {**self.counter, **counter}
        self.var_version_list = {**self.var_version_list, **var_version_list}

    def merge_from_others_records(self, ssa_record):
        """assume that the counter version is the var version.
        since the PhiStubBlock being inserted in every scope, we can safely assume that
        counter version is the latest version. See #mwf4g
        """
        for var, counter_ver in ssa_record.counter.items():
            latest_ver = counter_ver - 1
            var_stack = self.var_version_list.get(var)
            # current var version will take precedence over the other.
            # so if var stack exist for the variable, it means that var_version_list
            if var_stack is None:
                d = deque()
                d.append(latest_ver)
                self.var_version_list[var] = d
        self.counter = {**ssa_record.counter, **self.counter}

    def copy(self):
        """return an exact copy of current"""
        s = SsaBookKeeping()
        s.counter = self.counter.copy()
        s.var_version_list = copy.deepcopy(self.var_version_list)
        return s


class LocalsDictNode(BaseNode):
    """"""

    def __init__(self, lineno=None, col_offset=None, parent=None):
        super(LocalsDictNode, self).__init__(lineno, col_offset, parent)
        self.ssa_record = SsaBookKeeping()
        # list of containing scope e.g. FunctionDef/ClassDef
        self.containing_scope = []
        self.instance_dict = {}
        self.locals = {}
        # set containing variable that is labelled 'global'
        self.global_var = {}

    def scope(self):
        return self

    def get_version(self, var: str):
        """
        get the version number of the var, create the var entry if it's not exists
        """
        if var in self.ssa_record.var_version_list:
            version = (
                -1 if len(self.ssa_record.var_version_list[var]) == 0 else self.ssa_record.var_version_list[var][-1]
            )
        else:
            # might be referring to global, don't raise Exception
            version = -1
        return version

    def update_version(self, var: str):
        """
        increment the version of the var inside the dict and return the version number
        :param var:
        :param block_label:
        :return:
        """
        if var not in self.ssa_record.var_version_list and var not in self.ssa_record.counter:
            self.ssa_record.var_version_list[var] = deque((0,))
            self.ssa_record.counter[var] = 1
            version_number = 0
        else:
            i = self.ssa_record.counter[var]
            self.ssa_record.counter[var] += 1
            self.ssa_record.var_version_list.setdefault(var, deque()).append(i)
            version_number = i
        return version_number

    def remove_version(self, var, ver):
        var_stack = self.ssa_record.var_version_list.get(var)
        if var_stack is not None and ver in var_stack:
            var_stack.remove(ver)

    def get_latest_stmt(self, var: str):
        """return the latest statement in locals dict"""
        try:
            # use the counter instead of var_version_list to look at the latest stmt
            ver = self.ssa_record.counter[var] - 1
            return self.locals["{}_{}".format(var, ver)]
        except KeyError:
            val = self.locals.get(var)
            if val:
                return val
            raise exceptions.VariableNotExistStackError(var)

    def get_latest_stmt_from_stack(self, var: str):
        """Get the latest version from stack, and get the corresponding statement"""
        try:
            # use the counter instead of var_version_list to look at the latest stmt
            if var in self.ssa_record.var_version_list and len(self.ssa_record.var_version_list[var]) > 0:
                ver = self.ssa_record.var_version_list[var][-1]
                return self.locals["{}_{}".format(var, ver)]
            else:
                raise exceptions.VariableNotExistStackError(var)
        except KeyError:
            raise exceptions.VariableNotExistStackError(var)

    def resolve_instance(self):
        # nothing to resolve since it's not ClassInstance
        pass

    def create_latest_stmt(self, target: str, value: BaseNode):
        version = self.update_version(target)
        self.locals["{}_{}".format(target, version)] = value

    @classmethod
    def from_other_instance(cls, other_ins):
        c = cls()
        c.locals = other_ins.locals.copy()
        c.instance_dict = other_ins.instance_dict.copy()
        c.ssa_record = other_ins.ssa_record.copy()
        c.name = other_ins.name
        return c


class ClassInstance(LocalsDictNode, BaseInstance):
    _other_fields = ("obj", "call_context", "resolved", "target_cls")

    def __init__(self, obj=None, name=None):
        self.obj = obj
        self.resolved = False
        self.name = name
        self.target_cls = None
        super(ClassInstance, self).__init__()

    def merge_class_complete(self, context, cls, resolve_constructor=False):
        """merge attribute from a class completely
        Including merging the constructor if `resolve_constructor` is True
        """
        if cls.__class__.__name__ == "FunctionDef":
            # should call the function and use the instance returned from the function
            # this happen when the return value of a function is an instance e.g.
            # >>> s = get_instance() # <-- get_instance() is a function call
            # >>> s.some # <-- accessing the attribute of the returned instance
            # in inferring above, the `s` value will get inferred with `instance_mode`
            # therefore it's necessary to differentiate between class and function call.
            for ins in cls.infer_return_value(context):
                if ins.status and isinstance(ins.result, LocalsDictNode):
                    self.merge_cls(ins.result)
            # Copy the global variable record in the function and not the class.
            self.global_var = cls.global_var
            self.target_cls = cls
        elif cls.__class__.__name__ == "ClassDef":
            # There are 4 things to merge into the instance,
            # and it's arrange by it's precedence,
            # 1. the attribute assigned to instance outside constructor and
            #    class level attribute (self)
            # 2. the constructor (constructor.get_arg_instance(0)
            # 3. class level attribute (self.merge_cls(cls))
            # 4. The inherited class attributes
            if resolve_constructor:
                try:
                    constructor = cls.get_constructor()
                    ins = constructor.get_arg_instance(0)
                    self.merge_cls(ins)
                except (ValueError, exceptions.VariableNotExistStackError):
                    pass
            self.merge_cls(cls)
            for _mro_cls in cls._compute_mro(context)[1:]:
                self.merge_cls(_mro_cls)
            self.target_cls = cls

    def resolve_instance(self, context=None, resolve_constructor=False):
        """attempt to resolve the ClassDef location"""
        if self.resolved is False:
            try:
                # TODO: handle when instance has multiple values
                cls = next(self.obj.func.infer(context))
                if not cls.status:
                    return
                self.merge_class_complete(context, cls.result, resolve_constructor)
            except StopIteration:
                # can't resolve the instance
                return

    def merge_cls(self, cls):
        """Merge the locals, ssa_record and instance_dict from the ClassDef node
        `self` will have precedence over `cls`.
        """
        if isinstance(cls, LocalsDictNode):
            self.locals = {**cls.locals, **self.locals}
            self.ssa_record.merge_from_others_records(cls.ssa_record)
            self.instance_dict = {**cls.instance_dict, **self.instance_dict}
            self.global_var = cls.global_var
            if hasattr(cls, "resolved") and cls.resolved:
                # don't set resolved flag to true if the merging ClassInstance is
                # not resolved. This is to prevent class instance that depends on
                # some global value that at this point is not loaded. The
                # inference stage later on will try to inferred it again to get
                # the final value
                self.resolved = True

    def dunder_lookup(self, method):
        """resolve the dunder method with SSA version"""
        return self.get_latest_stmt(method)


class Uninferable:
    """class that represent invalid inference result"""

    def __init__(self, node=None, override_msg=None):
        self.msg = override_msg or "Inference failed for node: {}".format(node)

    def __hash__(self):
        """hash the class name since we want all uninferable to have the same hash"""
        return hash(self.__class__)

    def __repr__(self):
        return "Uninferable"

    def accept(self, visitor):
        raise NotImplementedError("type of node: {} has no visitor function".format(self))
