from Common.cfg_common import get_ast_node
from Common.common import *
from A4_CFG.var_ast import VarAst


class SsaCode:
    def __init__(self, as_tree=None, counter_dict=None, stack_dict=None):
        self.code_list = []
        self.var_version_list = stack_dict if stack_dict is not None else dict()
        self.counter = counter_dict if counter_dict is not None else dict()
        if as_tree is not None:
            self.add_ast(as_tree)

    def __repr__(self):
        s = ""
        for ssa in self.code_list:
            s = s + str(ssa) + '\n'

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
            self.var_version_list[var] = Stack(0)
            self.counter[var] = 1
            version_number = 0
        else:
            i = self.counter[var]
            self.counter[var] += 1
            self.var_version_list[var].push(i)
            version_number = i
        return version_number

    def get_version(self, var):
        """
        get the version number of the var, create the var entry if it's not exists
        :param var:
        :return:
        """
        if var in self.var_version_list:
            return self.var_version_list[var].peek()
        else:
            self.var_version_list[var] = Stack(0)
            self.counter[var] = 1
            return 0

    def get_line_ssa(self, line):
        return self.code_list[line]

    def add_ast(self, as_tree):
        for assign_node in as_tree.body:
            self.add_ast_node_ssa(assign_node)

    def add_ast_node(self, ast_node):
        """
        break ast stmt down and assign it to Ssa Class
        :param ast_node:
        :return:
        """
        params = VarAst(ast_node)

        left_var = params.left_operand if params.left_operand is not None else None

        right_var = params.right_operand if params.right_operand is not None else None

        if len(params.targets_var) != 0:
            target_var = params.get_target()
        else:
            target_var = None
        ssa_stmt = Ssa(target_var, left_var, params.body_op, right_var, target_operator=params.target_op)
        if ssa_stmt.is_not_none():
            self.code_list.append(ssa_stmt)

    def add_ast_node_by_line_number(self, as_tree, start_line, end_line):
        for i in range(start_line, end_line + 1):
            node = get_ast_node(as_tree, i)
            self.add_ast_node(node)

    def add_ast_node_ssa(self, ast_node):
        """
        break ast stmt down, transform to ssa and assign it to Ssa Class
        :param ast_node:
        :return:
        """

        params = VarAst(ast_node)

        if params.left_operand is not None:
            left_var = SsaVariable(params.left_operand, self.get_version(params.left_operand))
        else:
            left_var = params.left_operand

        if params.right_operand is not None:
            right_var = SsaVariable(params.right_operand, self.get_version(params.right_operand))
        else:
            right_var = params.right_operand

        if len(params.targets_var) != 0:
            target_var = SsaVariable(params.get_target(), self.update_version(params.get_target()))
        else:
            target_var = None
        ssa_stmt = Ssa(target_var, left_var, params.body_op, right_var, target_operator=params.target_op)
        self.code_list.append(ssa_stmt)

    @staticmethod
    def _get_assign_class(as_tree):
        for i in range(len(as_tree.body)):
            if isinstance(as_tree.body[i], ast.Assign):
                yield as_tree.body[i]

    def get_all_phi_functions(self):
        for ssa in self.code_list:
            if type(ssa) is PhiFunction:
                yield ssa

    def get_phi_function(self, var):
        for phi_func in self.get_all_phi_functions():
            if phi_func.var == var:
                return phi_func

    def fill_phi_param(self):
        for phi_func in self.get_all_phi_functions():
            phi_func.fill_param()

    def reload_stack_and_counter(self, stack, counter):
        self.var_version_list = stack
        self.counter = counter


class Ssa:
    def __init__(self, target, left, op, right, lvn_tuple=None, target_operator="Assign"):
        self.target = target
        self.target_operator = target_operator
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

    def __repr__(self):
        if self.target_operator == "Assign":
            s = ''
            if self.operator is None:
                s = s + str(self.target) + ' = ' \
                    + str(self.left_oprd)
            else:
                if self.left_oprd is not None:
                    s = s + str(self.target) + ' = ' \
                        + str(self.left_oprd) + ' ' + operator_dict[self.operator] \
                        + ' ' + str(self.right_oprd)
                else:
                    s = s + str(self.target) + ' = ' \
                        + operator_dict[self.operator] \
                        + ' ' + str(self.right_oprd)
            return s

        elif self.target_operator == "While" or self.target_operator == 'If':
            if self.operator is not None:
                return f"{self.target_operator} {self.left_oprd} {operator_dict[self.operator]} {self.right_oprd}"

            else:
                return f"{self.target_operator} {self.left_oprd}"

        else:
            return ""

    def is_not_none(self):
        if self.target is not None or self.left_oprd is not None or self.right_oprd is not None:
            return True
        return False


class SsaVariable:
    def __init__(self, var, version_num=0):
        self.var = var
        if not is_num(self.var):
            self.version_num = version_num

    def __repr__(self):
        if self.var is None:
            return None

        if is_num(self.var):
            return str(self.var)

        else:
            return self.var + '_' + str(self.version_num)

    def is_constant(self):
        return is_num(self.var)

    def get_var(self):
        if is_num(self.var):
            return self.var

        else:
            return self.var + '_' + str(self.version_num)


class PhiFunction(Ssa):
    def __init__(self, var, target=None, left_oprd=None, right_oprd=None):
        super().__init__(target, left_oprd, 'Phi', right_oprd)
        self.var = var

    def fill_param(self, param):
        if param.var != self.var:
            raise TypeError
        if self.left_oprd is None:
            self.left_oprd = param
            return
        else:
            self.right_oprd = param