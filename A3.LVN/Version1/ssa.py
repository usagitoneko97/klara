import ast


class Tac:
    def __init__(self, assign_node=None, lvn_tuple=None):
        self.target = None
        self.left_oprd = None
        self.right_oprd = None
        self.operator = None
        if assign_node is not None:
            self.init_by_ast(assign_node)
        elif lvn_tuple is not None:
            self.init_by_tuple(lvn_tuple)

    def init_by_tuple(self, lvn_tuple):
        self.target = lvn_tuple(0)
        self.left_oprd = lvn_tuple(1)
        self.operator = lvn_tuple(2)
        self.right_oprd = lvn_tuple(3)

    def init_by_ast(self, assign_node):
        self.target = assign_node.targets[0].id
        if isinstance(assign_node.value, ast.BinOp):
            self.version_number = 0
            self.left_oprd = str(self.get_var_or_num(assign_node.value.left))
            self.right_oprd = str(self.get_var_or_num(assign_node.value.right))
            self.operator = assign_node.value.op.__class__.__name__

        elif isinstance(assign_node.value, ast.Name) or isinstance(assign_node.value, ast.Num):
            self.left_oprd = self.get_var_or_num(assign_node.value)
            self.right_oprd = None
            self.operator = None

        elif isinstance(assign_node.value, ast.UnaryOp):
            self.left_oprd = None
            self.right_oprd = self.get_var_or_num(assign_node.value.operand)
            self.operator = assign_node.value.op.__class__.__name__

        elif isinstance(assign_node.value, ast.Compare):
            self.left_oprd = self.get_var_or_num(assign_node.value.left)
            self.right_oprd = self.get_var_or_num(assign_node.value.comparators[0])
            self.operator = assign_node.value.ops[0].__class__.__name__

    @staticmethod
    def get_var_or_num(value):
        if isinstance(value, ast.Name):
            return value.id
        else:
            return value.n

    def is_assignment(self):
        if self.target is None:
            return False
        return True

    def replace_rhs_expr(self, left_oprd, operator="", right_oprd=""):
        pass
