"""
Custom transform is applied after SSA, which allows the predicate function to
make use of SSA for maximum precision.
this also means that infer() is allowed in the specified transform function
since all necessary information have been set up during that time.
"""
import collections

from .manager import BaseManager

BASE_MANAGER = BaseManager()


class CustomTransform:
    """Recursively visit all node and apply transformation"""

    def __init__(self):
        self.transform_cache = collections.defaultdict(list)

    def _visit(self, node):
        if hasattr(node, "_fields"):
            for name in node._fields:
                value = getattr(node, name)
                returned = self._visit_generic(value)
                if returned != value:
                    setattr(node, name, returned)
        return self.transform(node)

    def _visit_generic(self, node):
        if isinstance(node, list):
            return [self._visit_generic(child) for child in node]
        if isinstance(node, tuple):
            return tuple(self._visit_generic(child) for child in node)
        if node is None or isinstance(node, str):
            return node
        return self._visit(node)

    def transform(self, node):
        cls = node.__class__
        if cls not in self.transform_cache or len(self.transform_cache[cls]) == 0:
            # reset the explicit inference in order for unregister to properly clear the tree
            if hasattr(node, "explicit_inference"):
                node.explicit_inference = None
            return node
        for trans_func, predicate in self.transform_cache[cls]:
            if predicate is None or predicate(node):
                BASE_MANAGER.logger.debug("AST", "Applying a transformation for node: '{}'", node)
                ret = trans_func(node)
                if ret is not None:
                    node = ret
                if ret.__class__ != cls:
                    break
        return node

    def register_transform(self, node_cls, trans_func, predicate=None):
        BASE_MANAGER.logger.debug("AST", "Registering transform for '{}' class with {}", node_cls.__name__, predicate)
        self.transform_cache[node_cls].append((trans_func, predicate))

    def unregister_transform(self, node_cls, trans_func, predicate=None):
        BASE_MANAGER.logger.debug(
            "AST", "Unregistering transform for '{}' class with {}", node_cls.__name__, trans_func
        )
        self.transform_cache[node_cls].remove((trans_func, predicate))

    def visit(self, module):
        """Walk the given *tree* and transform each encountered node
        Only the nodes which have transforms registered will actually
        be replaced or changed.
        """
        module = self._visit(module)
        return self.transform(module)
