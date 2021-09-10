import functools
import logging
import warnings

from klara.core import base_manager, context_mod

BASE_MANAGER = base_manager.BaseManager()


def inference_path(func):
    """record the inference path and avoid infinite recursion"""

    @functools.wraps(func)
    def wrapped(node, context=None, inferred_attr=None):
        yielded = set()
        if context is None:
            context = context_mod.InferenceContext()
        if context.push_path(node):
            return None

        for val in func(node, context, inferred_attr=inferred_attr):
            # after yielding a value, remove the path because the parent might have other operand that
            # will have the same exact path. After parent has done with the inference operation, add
            # the path again, to prevent recursion error on other operand. E.g.
            # x = 3 + y  # where y will eventually point back to this expression
            # after yielding 3, add back the node to path, so that when inferring y, it can detect the path
            context.remove_path(node)
            val.add_infer_path(node)
            if val not in yielded:
                BASE_MANAGER.infer_count += 1
                yield val
                yielded.add(val)
            context.push_path(node)
        context.remove_path(node)

    return wrapped


class cachedproperty:
    """Provides a cached property equivalent to the stacking of
    @cached and @property, but more efficient.

    After first usage, the <property_name> becomes part of the object's
    __dict__. Doing:

      del obj.<property_name> empties the cache.

    Idea taken from the pyramid_ framework and the mercurial_ project.

    .. _pyramid: http://pypi.python.org/pypi/pyramid
    .. _mercurial: http://pypi.python.org/pypi/Mercurial
    """

    __slots__ = ("wrapped",)

    def __init__(self, wrapped):
        try:
            wrapped.__name__
        except AttributeError as exc:
            raise TypeError("%s must have a __name__ attribute" % wrapped) from exc
        self.wrapped = wrapped

    @property
    def __doc__(self):
        doc = getattr(self.wrapped, "__doc__", None)
        return "<wrapped by the cachedproperty decorator>%s" % ("\n%s" % doc if doc else "")

    def __get__(self, inst, objtype=None):
        if inst is None:
            return self
        val = self.wrapped(inst)
        setattr(inst, self.wrapped.__name__, val)
        return val


def log_yielded_result(msg, *var, log_level=logging.INFO):
    """decorators to log the yield result for any func
    the yielded result is parsed as first argument. Use {0} in the string
    to place the yielded result. E.g.
    >>> @log_yielded_result("the function foo returned {0}. Extra is:{1}, {2}",
    ...                     "extra1", "extra2")
    ... def foo():
    ...     yield from [1, 2, 3]
    """

    def _(func):
        def wrapper(*args, **kwargs):
            for res in func(*args, **kwargs):
                formatted_msg = msg.format(res, *var)
                BASE_MANAGER.logger.log(level=log_level, msg=formatted_msg)

        return wrapper

    return _


def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used."""

    @functools.wraps(func)
    def new_func(*args, **kwargs):
        warnings.simplefilter("always", DeprecationWarning)  # turn off filter
        warnings.warn(
            "Call to deprecated function {}.".format(func.__name__), category=DeprecationWarning, stacklevel=2
        )
        warnings.simplefilter("default", DeprecationWarning)  # reset filter
        return func(*args, **kwargs)

    return new_func


def lru_cache_context(user_function):
    """cache the infer() returned results by comparing the state of the context.
    It's different than @functools.lru_cache since it's not comparing the object itself,
    but the state.
    All the relevant attribute in context are hashed, along with the unique_id of context for
    comparing different instances.
    """
    # object for determining failed cached retrieving, since `None` can't be used.
    sentinel = object()

    def _hash(node, context):
        if not context:
            return hash(id(node))
        call_chains = context.get_call_node_chain(node)
        _global_context_sets = frozenset()
        if context.globals_context.locals:
            _global_context_sets |= frozenset(context.globals_context.locals.items())
        return hash(
            (
                tuple(call_chains),
                _global_context_sets,
                id(node),
                context._id,
                frozenset({id(i) for i in context.inverted_conds}),
                context.conditions_mode,
                frozenset(context.decorator_ignore),
            ),
        )

    @functools.wraps(user_function)
    def wrapper(node, context=None, inferred_attr=None):
        if not hasattr(BASE_MANAGER.config, "force_infer") or not BASE_MANAGER.config.force_infer:
            if not context or not context.no_cache:
                key = _hash(node, context)
                result = BASE_MANAGER.infer_cache.get(key, sentinel)
                if result is not sentinel:
                    for res in result:
                        yield res
                    return
        # cached the result into a list
        results = []
        for res in user_function(node, context, inferred_attr):
            results.append(res)
            yield res
        if not hasattr(BASE_MANAGER.config, "force_infer") or not BASE_MANAGER.config.force_infer:
            if not context or not context.no_cache:
                BASE_MANAGER.infer_cache[key] = results

    return wrapper


def yield_at_least_once(node_class):
    def _w(f):
        def wrapper(node, *args, **kwargs):
            yielded = False
            for res in f(node, *args, **kwargs):
                yielded = True
                yield res
            if not yielded:
                yield node_class(node)

        return wrapper

    return _w
