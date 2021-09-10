import collections
import enum

from . import exceptions, nodes, utilities
from .config import Config


class ConditionsMode(enum.Enum):
    """Enum for status in expanding conditions"""

    DISABLE = -1
    ENABLE = 1
    IN_PROGRESS = 2


class InferenceContext(object):
    """manages context for analyzing different scope"""

    id = 0

    __slots__ = (
        "call_context",
        "bound_instance",
        "globals_context",
        "instance_mode",
        "config",
        "decorator_ignore",
        "path",
        "cache",
        "is_node_ignore_mode",
        "_id",
        "inverted_conds",
        "model",
        "no_cache",
        "conditions_mode",
        "z3_model_used",
        "call_chain",
        "z3_result_hash",
    )

    def __init__(
        self,
        call_context=None,
        bound_instance=None,
        global_context=None,
        instance_mode=False,
        config=None,
        decorator_ignore=None,
        node_ignore=None,
        is_node_ignore_mode=False,
    ):
        self.call_context = call_context if call_context else {}
        self.bound_instance = bound_instance
        # global context is used to store the context just before any call.
        self.globals_context = global_context if global_context else GlobalContext()
        self.instance_mode = instance_mode
        self.config = config if config else Config()
        # used to signal which FunctionDef would treated as a normal non-decorative func
        # This is also helping to differentiate between inferring a functiondef to get the wrapped
        # decorator result and inferring the function without decorator (when passing the
        # original function into the decorator func)
        # see (#vqca3)
        self.decorator_ignore = decorator_ignore or set()
        self.path = set()
        # node ignored will be substituted to the field
        # specified by the decorators @substitute(["field"])
        self.is_node_ignore_mode = is_node_ignore_mode
        # unique id for each object. Used guarantee comparison between 2 context object always stand.
        self._id = InferenceContext.id
        self.inverted_conds = set()
        InferenceContext.id += 1
        self.model = None
        self.no_cache = False
        self.conditions_mode = ConditionsMode.ENABLE
        self.z3_model_used = {}
        self.call_chain = collections.OrderedDict()
        self.z3_result_hash = None

    def map_args_to_func(self, *args, kwargs=None, func_node=None, offset=0, remove_default=True):
        """
        map arbitrary number of args to the target func_node.
        :param args: positional arguments for mapping to func_node
        :param func_node: the target function
        :param offset: offset of args in target_func
        :param remove_default: flag to determine whether to remove arg in call_context
        :return: True if type matches, False if otherwise.
        """
        match = False
        for call_arg, func_arg in zip(args, func_node.args.args[offset:]):
            match = utilities.is_match_call(call_arg, func_arg)
            self.call_context[func_arg] = call_arg
        # if call_arg is less than func_arg, the default arg of
        # func_arg will be used. Thus the arg need to be removed
        # in call_context
        if len(args) < (len(func_node.args.args) - offset) and remove_default:
            for func_arg in list(reversed(func_node.args.args))[: len(func_node.args.args) - len(args) - offset]:
                try:
                    self.call_context.pop(func_arg)
                except KeyError:
                    pass
        if kwargs and type(kwargs) is list:
            for keyword in kwargs:
                # let the StopIteration exception throw to caller to handle
                index = func_node.args.get_index_of_arg(keyword.arg)
                if index:
                    self.call_context[func_node.args.args[index]] = keyword.value
        return match

    def map_call_node_to_func(self, call_node, func_node, instance=None, class_instance=None):
        """match the arg from call to args from FunctionDef."""
        if isinstance(func_node, nodes.ClassDef):
            # call to class. Get the constructor
            try:
                func = func_node.get_constructor()
                if isinstance(func, nodes.OverloadedFunc):
                    for f in func.elts:
                        if self.map_args_to_func(class_instance, func_node=f, remove_default=False):
                            return
                    # reach here if all __init__ doesn't match call arguments.
                    # Can use any of the function in overloaded_func
                    func = func.elts[-1]
                # map the `self` argument
                else:
                    self.map_args_to_func(class_instance, func_node=func, remove_default=False)
                offset = 1
            except exceptions.VariableNotExistStackError:
                # call to Class didn't have constructor
                return
        elif isinstance(func_node, nodes.FunctionDef):
            if func_node.type == "method":
                self.map_args_to_func(instance, func_node=func_node, remove_default=False)
                offset = 1
            else:
                offset = 0
            func = func_node
        elif isinstance(func_node, nodes.Lambda):
            offset = 0
            func = func_node
        else:
            # not a function/class, no arguments to map
            return
        self.map_args_to_func(*call_node.args, kwargs=call_node.keywords, func_node=func, offset=offset)

    def reload_context(self, call_stmt: nodes.Call, dest_stmt, instance=None, class_instance=None):
        """make sure that the locals in must be the subset of the scope locals. See #mr9ac"""
        # FIXME: instance using the locals get from call_stmt.locals.instance
        if "scope" in call_stmt.locals:
            scope_local = call_stmt.locals["scope"]
            self.map_call_node_to_func(call_stmt, dest_stmt, instance, class_instance)
            try:
                for keys, items in scope_local.items():
                    if dest_stmt.parent:
                        assert dest_stmt.parent.scope().locals.get(keys) == items
                    else:
                        return
            except AssertionError:
                return
            self.globals_context.locals = scope_local
            self.globals_context.ssa_record = call_stmt.ssa_record

    def remove_context(self, func_node):
        if isinstance(func_node, nodes.ClassDef):
            try:
                func_node = func_node.get_constructor()
            except exceptions.VariableNotExistStackError:
                return
        if func_node:
            for arg in func_node.args.args:
                if arg in self.call_context:
                    self.call_context.pop(arg)

    def hash_call_context(self):
        return hash(frozenset(self.call_context.items()))

    def push_path(self, node):
        """to handle the inference path.
        :return: True if node is already in context path else False
        :rtype: bool
        """
        call_context_hash = self.hash_call_context()
        if (node, call_context_hash) in self.path:
            return True
        self.path.add((node, call_context_hash))
        return False

    def remove_path(self, node):
        try:
            self.path.remove((node, self.hash_call_context()))
        except KeyError:
            pass

    def add_call_chain(self, call_node, func_node):
        self.call_chain[func_node] = call_node

    def remove_call_chain(self, call_node):
        if call_node in self.call_chain:
            self.call_chain.pop(call_node)

    def get_call_node_chain(self, any_node):
        try:
            scope = any_node.scope()
            if not isinstance(scope, nodes.FunctionDef):
                return []
            calls = []
            found = False
            for func, call_node in self.call_chain.items():
                calls.append(call_node)
                if isinstance(func, nodes.Proxy):
                    func = func.obj
                if func == scope:
                    found = True
                    break
            return calls if found else []
        except AttributeError:
            return []


class GlobalContext:
    """Class to store global variable for other scope"""

    __slots__ = ("ssa_record", "locals")

    def __init__(self, ssa_record=None, locals=None):
        self.ssa_record = ssa_record
        self.locals = locals

    def get_latest_stmt(self, var: str):
        """return the latest statement in locals dict
        Raise exceptions.VariableNotExistStackError if it's not in locals
        Raise
        """
        try:
            ver = self.ssa_record.var_version_list[var][-1]
            return self.locals["{}_{}".format(var, ver)]
        except KeyError:
            # get directly from locals in the case of it had not been renamed
            val = self.locals.get(var)
            if val:
                return val
            raise exceptions.VariableNotExistStackError(var)
        except AttributeError:
            raise exceptions.VariableNotExistStackError(var)


context_ins = InferenceContext()
