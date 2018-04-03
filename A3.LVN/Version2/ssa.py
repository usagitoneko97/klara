import ast
from common import *

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
                s = s + str(assign_ssa.target) + ' = ' \
                    + str(assign_ssa.left_oprd) + '\n'
            else:
                if assign_ssa.left_oprd is not None:
                    s = s + str(assign_ssa.target) + ' = ' \
                        + str(assign_ssa.left_oprd) + ' ' + str(assign_ssa.operator) \
                        + ' ' + str(assign_ssa.right_oprd) + '\n'
                else:
                    s = s + str(assign_ssa.target ) + ' = ' \
                        + str(assign_ssa.operator) \
                        + ' ' + str(assign_ssa.right_oprd) + '\n'

        return s

    def __iter__(self):
        for ssa in self.code_list:
            yield ssa

    def get_stmt_param_from_ast(self, assign_node):
        """
        get the target, left operand, operator and right operand from an assign node
        :param assign_node:
        :return: target, left op, right
        """
        target = assign_node.targets[0].id
        if isinstance(assign_node.value, ast.BinOp):
            left_oprd = get_var_or_num(assign_node.value.left)
            right_oprd = get_var_or_num(assign_node.value.right)
            operator = assign_node.value.op.__class__.__name__

        elif isinstance(assign_node.value, ast.Name) or isinstance(assign_node.value, ast.Num):
            left_oprd = get_var_or_num(assign_node.value)
            right_oprd = None
            operator = None

        elif isinstance(assign_node.value, ast.UnaryOp):
            left_oprd = None
            right_oprd = get_var_or_num(assign_node.value.operand)
            operator = assign_node.value.op.__class__.__name__

        elif isinstance(assign_node.value, ast.Compare):
            left_oprd = get_var_or_num(assign_node.value.left)
            right_oprd = get_var_or_num(assign_node.value.comparators[0])
            operator = assign_node.value.ops[0].__class__.__name__

        return target, left_oprd, operator, right_oprd

    def ssa_index_is_assignment(self, index):
        return self.code_list[index].is_assignment()

    def update_version(self, var):
        """
        increment the version of the var inside the dict and return the version number
        :param var:
        :return:
        """
        if var not in self.var_version_list:
            self.var_version_list[var] = 0
            version_number = 0
        else:
            self.var_version_list[var] += 1
            version_number = self.var_version_list[var]
        return version_number

    def get_version(self, var):
        """
        get the version number of the var, create the var entry if it's not exists
        :param var:
        :return:
        """
        if var in self.var_version_list:
            return self.var_version_list[var]
        else:
            self.var_version_list.__setitem__(var, 0)
            return 0

    def get_line_ssa(self, line):
        return self.code_list[line]

    def add_ssa(self, as_tree):
        for assign_node in as_tree.body:
            target, left, op, right = self.get_stmt_param_from_ast(assign_node)

            left_var, right_var = None, None

            if left is not None:
                left_var = SsaVariable(left, self.get_version(left))
            if right is not None:
                right_var = SsaVariable(right, self.get_version(right))

            target_var = SsaVariable(target, self.update_version(target))

            assign_ssa = Ssa(target_var, left_var, op, right_var)
            self.code_list.append(assign_ssa)

    @staticmethod
    def _get_assign_class(as_tree):
        for i in range(len(as_tree.body)):
            if isinstance(as_tree.body[i], ast.Assign):
                yield as_tree.body[i]


class Ssa:
    def __init__(self, target, left, op, right, lvn_tuple=None):
        self.target = target
        self.left_oprd = left
        self.operator = op
        self.right_oprd = right

        if lvn_tuple is not None:
            self.init_by_tuple(lvn_tuple)

    def init_by_tuple(self, lvn_tuple):
        self.target = lvn_tuple(0)
        self.left_oprd = lvn_tuple(1)
        self.operator = lvn_tuple(2)
        self.right_oprd = lvn_tuple(3)

    def is_assignment(self):
        if self.target is None:
            return False
        return True

    def replace_rhs_expr(self, left_oprd, operator="", right_oprd=""):
        pass


class SsaVariable:
    def __init__(self, var, version_num=0):
        self.var = var
        if not is_num(self.var):
            self.version_num = version_num

    def __str__(self):
        if is_num(self.var):
            return str(self.var)

        else:
            return self.var + '_' + str(self.version_num)

    def __repr__(self):
        if is_num(self.var):
            return str(self.var)

        else:
            return self.var + '_' + str(self.version_num)

    def is_constant(self):
        return is_num(self.var)

