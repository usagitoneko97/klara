from klara.core import exceptions

from .base_manager import BaseManager
from .ssa_visitors import AstVisitor

BASE_MANAGER = BaseManager()


def link_stmts_to_def(ssa, allow_uninitialized=False, target_phi=False):
    """
    link statement given to its defining variable in locals_dict or globals_dict
    :param ssa: the statement
    :param allow_uninitialized: if True: will throw an exception when variable is uninitialized, will initialized to
    ver number 0 if False
    :param target_phi: if true, only link phi statements
    :return: None because it only modify attr in ssa
    """
    if (target_phi is True and ssa.statement().is_phi is True) or (
        target_phi is False and ssa.statement().is_phi is False
    ):
        DefUseLinker.link(ssa, allow_uninitialized)


class DefUseLinker(AstVisitor):
    """link a variable to its definition including other scope"""

    def __init__(self, allow_uninitialized=False):
        self.allow_uninitialized = allow_uninitialized

    @classmethod
    def link(cls, node, allow_uninitialized=False):
        c = cls(allow_uninitialized)
        try:
            c.visit(node)
        except exceptions.InstanceNotExistError:
            BASE_MANAGER.logger.warning("SSA", "failed to get the instance of node: " + str(node))

    def visit_attribute(self, node):
        self.visit(node.value)
        if not node.is_name_constant():
            def_stmt = node.instance().locals.get(node.get_var_repr())
            node.links = def_stmt

    def visit_name(self, node):
        if not node.is_name_constant():
            def_stmt = node.instance().locals.get(node.get_var_repr())
            node.links = def_stmt

    def visit_subscript(self, node):
        self.generic_visit(node)
        if node.is_load_var():
            def_stmt = node.instance().locals.get(str(node))
            node.links = def_stmt


def link(node):
    if not node.is_name_constant():
        try:
            def_stmt = node.instance().locals.get(node.get_var_repr())
            node.links = def_stmt
        except (exceptions.InstanceNotExistError, NotImplementedError, AttributeError):
            # can't link since there is no instance
            pass
