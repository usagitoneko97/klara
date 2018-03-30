import ast


class SsaCode:
    def __init__(self, as_tree=None):
        self.code_list = []
        self.var_version_list = dict()
        if as_tree is not None:
            self.add_ssa(as_tree)

    def __repr__(self):
        s = ""
        for assign_ssa in self.code_list:
            if assign_ssa.operator is None:
                s = s + assign_ssa.target + ' = ' \
                    + str(assign_ssa.left_oprd) + '\n'
            else:
                if assign_ssa.left_oprd is not None:
                    s = s + assign_ssa.target + ' = ' \
                        + str(assign_ssa.left_oprd) + ' ' + str(assign_ssa.operator) \
                        + ' ' + str(assign_ssa.right_oprd) + '\n'
                else:
                    s = s + assign_ssa.target + ' = ' \
                        + str(assign_ssa.operator) \
                        + ' ' + str(assign_ssa.right_oprd) + '\n'

        return s

    def __iter__(self):
        for ssa in self.code_list:
            yield ssa

    def ssa_index_is_assignment(self, index):
        return self.code_list[index].is_assignment()

    def update_version(self, assign_node, assign_ssa):
        if assign_node.targets[0].id not in self.var_version_list:
            self.var_version_list[assign_node.targets[0].id] = 0
            assign_ssa.version_number = 0
        else:
            self.var_version_list[assign_node.targets[0].id] += 1
            assign_ssa.version_number = self.var_version_list[assign_node.targets[0].id]

    def get_version(self, var):
        if var in self.var_version_list:
            return self.var_version_list[var]
        else:
            return -1

    def get_line_ssa(self, line):
        return self.code_list[line]

    def add_ssa(self, as_tree):
        for assign_node in as_tree.body:
            assign_ssa = Ssa(assign_node)
            self.update_version(assign_node, assign_ssa)
            self.code_list.append(assign_ssa)

    @staticmethod
    def _get_assign_class(as_tree):
        for i in range(len(as_tree.body)):
            if isinstance(as_tree.body[i], ast.Assign):
                yield as_tree.body[i]


class Ssa:
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
            self.left_oprd = self.get_var_or_num(assign_node.value.left)
            self.right_oprd = self.get_var_or_num(assign_node.value.right)
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
