from . import base_manager, exceptions, nodes
from .bases import BaseNode

BASE_MANAGER = base_manager.BaseManager()


class AstVisitor:
    def visit(self, node):
        method = "visit_" + node.__class__.__name__.lower()
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        for field, value in node.iter_fields():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, BaseNode):  # noqa: F405
                        self.visit(item)
            elif isinstance(value, BaseNode):  # noqa: F405
                self.visit(value)


class VariableGetter(AstVisitor):
    """get all variables (ast.name) from given node, separate by targets and values"""

    def __init__(self):
        self.targets = []
        self.values = []
        self.current_loc = self.values  # default location to store the found variable

    @classmethod
    def get_variable(cls, node):
        c = cls()
        c.visit(node)
        return c

    def visit_name(self, node):
        self.values.append(node)

    def visit_assignname(self, node):
        self.targets.append(node)

    def visit_attribute(self, node):
        self.visit(node.value)
        self.values.append(node)

    def visit_assignattribute(self, node):
        self.visit(node.value)
        self.targets.append(node)


class AstAttrSeparator(AstVisitor):
    """
    Separate all attr and organize them based on ctx. E.g.,
    a.b = c.d
    will yield
    a  ->  Load
    a.b -> store
    c  ->  Load
    c.d -> Load
    """

    def __init__(self):
        self.load = set()
        self.store = set()
        self._base = ""

    def visit_attribute(self, node):
        self.visit(node.value)
        self.load.add(node)

    def visit_assignattribute(self, node):
        self.visit(node.value)
        self.store.add(node)

    def visit_name(self, node):
        self.load.add(node)

    def visit_assignname(self, node):
        self.store.add(node)


class TargetRemover(AstVisitor):
    """Remove any variable that has ast.Store() from provided stack_dict"""

    def visit_assignattribute(self, node):
        try:
            node.instance().remove_version(node.attr, node.version)
        except exceptions.InstanceNotExistError:
            BASE_MANAGER.logger.warning("SSA", "failed to get the instance of node: " + str(node))

    def visit_assignname(self, node):
        try:
            node.instance().remove_version(node.id, node.version)
        except exceptions.InstanceNotExistError:
            BASE_MANAGER.logger.warning("SSA", "failed to get the instance of node: " + str(node))


class NodeFinder(AstVisitor):
    """Find any node given the function to match"""

    def __init__(self, func_to_match):
        self.func_to_match = func_to_match
        self.found_node = None

    def generic_visit(self, node):
        if self.func_to_match(node):
            self.found_node = node
        if not isinstance(node, nodes.Variable):
            # skip variable since those are the items that we target
            super(NodeFinder, self).generic_visit(node)

    def execute(self, node):
        self.visit(node)
        return self.found_node


class StatementExprExtractor(AstVisitor):
    def __init__(self, statement_lines: dict):
        self.statement_lines = statement_lines
        self.collected_nodes = {}
        self.counter = -1

    def extract(self, node):
        self.visit(node)
        from collections import namedtuple

        key, value = [], []
        for k, v in self.collected_nodes.items():
            key.append(k)
            value.append(v)
        key.append("module")
        value.append(node)
        t = namedtuple("ast", key)
        return t(*value)

    def generic_visit(self, node):
        if node.lineno in self.statement_lines:
            name, member = self.statement_lines[node.lineno]
            name = name or self._make_random_name()
            value = getattr(node, member) if member else node
            self.collected_nodes[name] = value
            del self.statement_lines[node.lineno]
        super(StatementExprExtractor, self).generic_visit(node)

    def _make_random_name(self):
        self.counter += 1
        return "no_name_" + str(self.counter)
