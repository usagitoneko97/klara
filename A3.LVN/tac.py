import ast


class SsaCode:
    def __init__(self, as_tree):
        self.code_list = []
        self.var_version_list = dict()
        self.add_ssa(as_tree)

    def __repr__(self):
        s = ""
        for assign_ssa in self.code_list:
            s = s + assign_ssa.target + str(assign_ssa.version_number) + '=' \
                + assign_ssa.left_oprd + assign_ssa.operator \
                + assign_ssa.right_oprd + '\n'

        return s

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
    def __init__(self, assign_node):
        if isinstance(assign_node.value, ast.BinOp):
            self.version_number = 0
            self.target = assign_node.targets[0].id
            self.left_oprd = self.get_var_or_num(assign_node.value.left)
            self.right_oprd = self.get_var_or_num(assign_node.value.right)
            self.operator = assign_node.value.op.__class__.__name__
        elif isinstance(assign_node.value, ast.Name):
            self.left_oprd = assign_node.value.id

    @staticmethod
    def get_var_or_num(value):
        if isinstance(value, ast.Name):
            return value.id
        else:
            return str(value.n)

    def is_assignment(self):
        if self.target is None:
            return False
        return True

    def replace_rhs_expr(self, left_oprd, operator="", right_oprd=""):
        pass
