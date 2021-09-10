import contextlib
import importlib
import itertools
from functools import singledispatch, update_wrapper
from xml.etree import ElementTree

import z3

from klara.core import nodes


def methdispatch(func):
    dispatcher = singledispatch(func)

    def wrapper(*args, **kw):
        return dispatcher.dispatch(args[1].__class__)(*args, **kw)

    wrapper.register = dispatcher.register
    update_wrapper(wrapper, func)
    return wrapper


def compare_inferred_node(node, constant):
    if isinstance(node, nodes.Const):
        return node.value == constant
    return False


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def is_match_call(node1: nodes.BaseNode, node2, context=None) -> bool:
    # check for all possible combination of the annotation
    # and return True if one of the combination matches.
    if node1 and node2.annotation:
        for left, right in itertools.product(node1.infer(context), node2.annotation.infer(context)):
            if left.result_type == right.result:
                return True
        return False


class ElementTreeRepr(ElementTree.ElementTree):
    """Override ElementTree with added str representation."""

    def __init__(self, element=None, file=None):
        self.file = file
        super(ElementTreeRepr, self).__init__(element, file)

    def __repr__(self):
        try:
            return str(self.file.name)
        except AttributeError:
            return str(self.file)


def is_subset(main_container: set, container_checker: set) -> set:
    """cancel element in main container that is subset/superset to the container_checker"""
    result = main_container.copy()
    for main, checker in itertools.product(main_container, container_checker):
        if main in checker or checker in main:
            result.remove(main)
    return result


class TempAttr:
    """Temporary set multiple attribute of an obj.
    Example:
        with TempAttr(node) as handler:
            handler.set_attr("temp", 2)
    """

    def __init__(self, obj):
        self.obj = obj
        # dict map from attr to backup
        self._attr_changed = {}
        # set to indicate the attr had not been set before
        self._empty_attr = set()

    def __enter__(self):
        self.backup = self.obj.__dict__.copy()
        return self

    def set_attr(self, attr, value):
        obj_map = self.obj.__dict__ if hasattr(self.obj, "__dict__") else self.obj.__slots__
        if attr in obj_map:
            self._attr_changed[attr] = getattr(self.obj, attr)
        else:
            self._empty_attr.add(attr)
        setattr(self.obj, attr, value)

    def __exit__(self, exc_type, exc_val, exc_tb):
        for empty_attr in self._empty_attr:
            delattr(self.obj, empty_attr)
        for attr, backup in self._attr_changed.items():
            setattr(self.obj, attr, backup)


def make_import_optional(name, package=None, manager=None):
    """optionally import module, log the warning message if it's not imported"""
    try:
        return importlib.import_module(name, package)
    except SystemError:
        # for some reason import_module need to specifically import package
        # before performing relative import
        try:
            importlib.import_module(package)
            return importlib.import_module(name, package)
        except (ModuleNotFoundError, SystemError):
            pass
    except ModuleNotFoundError:
        pass

    class Wrap:
        def __call__(self, *args, **kwargs):
            if manager:
                manager.logger.error("INITIALIZE", "Module: {} is not installed.", package)

        def __getattr__(self, item):
            if manager:
                manager.logger.error("INITIALIZE", "Module: {} is not installed.", package)

    return Wrap()


@contextlib.contextmanager
def temp_config(manager, config):
    backup = manager.config
    manager.config = config
    yield
    manager.config = backup
    manager.reload_protocol()


def check_selected_operand(results):
    """
    check selected_operand in the results to see if they're matched
    :param results: can be list of (InferenceResult or dict)
    :return: bool
    """

    def _hash_to_set(v):
        if type(v) is set:
            return set(hash(va) for va in v)
        else:
            return {hash(v)}

    def _check_conflict(ds):
        if len(ds) > 1:
            all_items = ds[0].copy()
        else:
            return True
        for d in ds[1:]:
            for k in all_items.keys() & d:
                val_left, val_right = _hash_to_set(all_items[k]), _hash_to_set(d[k])
                if len(val_left & val_right) == 0:
                    return False
            all_items.update(d)
        return True

    all_dicts = []
    for res in results:
        if hasattr(res, "selected_operand"):
            all_dicts.append(res.selected_operand)
        elif isinstance(res, dict):
            all_dicts.append(res)
    return _check_conflict(all_dicts)


def infer_product(*iterators, disable_caching=False):
    """implementation of products of operand in binop/boolop/compare etc..."""
    if not disable_caching:
        for product_it in itertools.product(*iterators):
            if check_selected_operand(product_it):
                yield product_it
    else:
        yield from itertools.product(*iterators)


def strip_constant_node(node):
    """FOr ast const node, get the actual python const"""
    if isinstance(node, (nodes.Const, nodes.NameConstant)):
        return node.value
    elif isinstance(node, nodes.ClassInstance):
        return node
    elif isinstance(node, nodes.BaseContainer):
        return node.get_actual_container()
    else:
        return node


def combine_inference_results(results):
    z3_assumptions = set()
    for val in results:
        if len(val.z3_assumptions) == 1:
            z3_assumptions.add(list(val.z3_assumptions)[0])
        elif len(val.z3_assumptions) > 1:
            z3_assumptions.add(z3.And(val.z3_assumptions))
    if len(z3_assumptions) > 0:
        z3_or = z3.Or(z3_assumptions)
        res = results[0].__class__.from_other(results[0], inference_results=results)
        res.z3_assumptions = {z3_or}
    else:
        res = results[0]
    return res


class SubsetTree:
    """
    construct a tree that start with the total subset, and children will be the subset of the parent node.
    In case where some set is subset to multiple node, it will insert to all of the nodes.
    Most of it is taken from: https://stackoverflow.com/a/51648211/9677833
    """

    def __init__(self, key, all_key=False, index=None):
        self.all = all_key
        self.key = key
        self.children = []
        self.index = index

    def add_children(self, node):
        self.children.append(node)

    def __repr__(self):
        return "key: {}, children: {}".format(self.key, self.children)

    def issubset(self, query):
        if not self.all:
            return query.issubset(self.key)
        return True

    def longest_subsets(self, query):
        yielded = False
        for child in self.children:
            if child.issubset(query):
                yielded = True
                yield child
        if not yielded:
            yield self

    def all_subsets(self, paths=None):
        paths = paths or []
        if len(self.key) > 0:
            paths.append(self.key)
        for c in self.children:
            yield from c.all_subsets(paths)
        if not self.children:
            yield paths.copy()
        if len(self.key) > 0:
            paths.pop()

    def all_children(self):
        for child in self.children:
            yield child
            yield from child.all_children()

    @classmethod
    def build_sub_tree(cls, lits: list):
        sets = sorted(lits, key=lambda x: len(x[1]), reverse=True)
        tree = cls(frozenset(), all_key=True)
        for i, s in sets:
            node = SubsetTree(s, index=i)
            for children in list(tree.longest_subsets(s)):
                children.children.append(node)
        return tree


def compare_variable(a, b):
    return repr(a) == repr(b)


def build_sub_list(sets: list):
    groups = []
    for i, aSet in sorted(sets, key=lambda x: len(x[1]), reverse=True):
        clusters = [g for g in groups if g[0][1].issuperset(aSet)]
        if not clusters:
            groups.append([])
            clusters = groups[-1:]
        for g in clusters:
            g.append((i, aSet))
    return groups


def get_py_val_from_z3_val(z3_result):
    if z3_result is not None:
        if z3.is_int_value(z3_result):
            return z3_result.as_long()
        elif z3.is_real(z3_result):
            return float(z3_result.numerator_as_long()) / float(z3_result.denominator_as_long())
        elif z3.is_true(z3_result):
            return True
        elif z3.is_false(z3_result):
            return False
        elif z3.is_string_value(z3_result):
            return z3_result.as_string()
        else:
            raise NotImplementedError("Z3 model result other than int, real, bool, string is not supported yet!")


Z3CONST_MAP = {int: z3.IntVal, float: z3.RealVal, str: z3.StringVal, bool: z3.BoolVal}
ASTBOOL2Z3_MAP = {"or": z3.Or, "and": z3.And}
AST2Z3TYPE_MAP = {int: z3.Int, float: z3.Real, bool: z3.Bool, str: z3.String}


def make_z3_const(value):
    if type(value) in Z3CONST_MAP:
        z3_var_type = Z3CONST_MAP.get(type(value))
        if not z3_var_type:
            raise NotImplementedError("Type other than int, float, bool and string is not supported yet!")
        return z3_var_type(value)
    else:
        return value


def make_z3_boolvar(op, values):
    z3_bool = ASTBOOL2Z3_MAP.get(op)
    if z3_bool:
        return z3_bool(*values)
    else:
        raise TypeError("unknown operand: {}".format(op))
