from common import *


class VariableDict(dict):
    def __init__(self, ssa_code=None):
        self.current_value = 0
        self.val_num_var_list = []
        if ssa_code is not None:
            self.enumerate_rhs(ssa_code)
        dict.__init__(self)

    def _add_to_variable_dict(self, ssa_var):
        if self.get(str(ssa_var)) is None:
            self.__setitem__(str(ssa_var), self.current_value)
            self.val_num_var_list.append(str(ssa_var))
            self.current_value += 1

    def enumerate(self, ssa):
        if ssa.left_oprd is not None:
            self._add_to_variable_dict(ssa.left_oprd)

        if ssa.right_oprd is not None:
            self._add_to_variable_dict(ssa.right_oprd)

        self._add_to_variable_dict(ssa.target)

    def get_value_number(self, var):
        """
        return enumerated value number for the var
        :param var:
        :return:
        """
        return self.__getitem__(var)

    def get_variable(self, val_num):
        return self.val_num_var_list[val_num]


class LvnCodeTupleList(list):
    def append_lvn_stmt(self, lvn_stmt):
        self.append((lvn_stmt.target, lvn_stmt.left, lvn_stmt.operator,
                     lvn_stmt.right))


class SimpleAssignDict(dict):
    def find_substitute(self, val_num):
        subs = self.get(val_num)
        if subs is None:
            return val_num
        return subs

    def update_simp_assgn(self, target, var):
        self.__setitem__(target, var)


class LvnDict(dict):
    def __init__(self, ssa=None):
        # enumerate ssa_code
        if ssa is not None:
            self.variable_dict = VariableDict(ssa)
        self.variable_dict = VariableDict()
        self.simple_assign_dict = SimpleAssignDict()
        self.lvn_code_tuples_list = LvnCodeTupleList()
        dict.__init__(self)

    def get_eq_var(self, curr_var):
        """
        get equal value of variable or number of curr_var
        :param curr_var : the current variable to search on the dict
        :return: Another var or num associate with curr_var
        """
        if self.variable_dict[curr_var] in self.simple_assign_dict:
            # search on the simple assign dict whether it has another variable associate with it
            simple_assign_list = self.simple_assign_dict[self.variable_dict[curr_var]]

            return self.variable_dict.get_variable_or_constant(simple_assign_list)

    def replace_var(self, oprd):
        """
        replace the var with any equivalent var
        :param oprd:
        :return: The replaced var.
        """
        if self.variable_dict.get_value_number(oprd) in self.simple_assign_dict:
            # search on the simple assign dict whether it has another variable associate with it
            simple_assign_list = self.simple_assign_dict[
                self.variable_dict.get_value_number(oprd)]

            oprd = self.variable_dict.get_variable_or_constant(simple_assign_list)
        return oprd

    def get_lvn_stmt(self, ssa):
        target = self.variable_dict.get(str(ssa.target))
        left_oprd, right_oprd = None, None

        if ssa.left_oprd is not None:
            left_oprd = self.variable_dict.get(str(ssa.left_oprd))

        if ssa.right_oprd is not None:
            right_oprd = self.variable_dict.get(str(ssa.right_oprd))

        lvn_stmt = LvnStatement(target, left_oprd, ssa.operator, right_oprd)
        return lvn_stmt

    def add_expr(self, expr, target):
        self.__setitem__(expr, target)

    def get_var(self, lvn_stmt_str):
        # perform search on dict, use the value returned to search on variable_dict and return
        pass

    def find_substitute(self, lvn_stmt):
        lvn_var = self.get(lvn_stmt.get_expr())
        if lvn_var is not None:
            lvn_stmt.replace_expr(lvn_var)
        return lvn_stmt


class LvnStatement:
    def __init__(self, target, left, operator, right):
        self.left = left
        self.right = right
        self.operator = operator
        self.target = target

    def get_expr(self):
        if self.operator is None:
            return str(self.left)
        return str(self.left) + self.operator + str(self.right)

    def __repr__(self):
        if self.operator is None:
            return str(self.target) + ' = ' + str(self.left)
        return str(self.target) + ' = ' + str(self.left) + self.operator + str(self.right)

    def is_simple_assignment(self):
        if self.operator is None:
            return True
        return False

    def replace_expr(self, stmt_Vn):
        self.left = stmt_Vn
        self.right, self.operator = None, None

    def reorder(self):
        operands_list = [self.left, self.right]
        operands_list.sort()
        self.left = operands_list[0]
        self.right = operands_list[1]

    def reorder_selected_operands(self):
        if self.operator is not None:
            if self.operator == 'Add' or \
               self.operator == 'Mult'or \
               self.operator == 'BitOr' or \
               self.operator == 'BitXor' or \
               self.operator == 'BitAnd':

                self.reorder()
