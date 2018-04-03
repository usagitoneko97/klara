from common import *
import copy


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

    def enumerate_lhs(self, ssa):
        if self.get(str(ssa.target)) is not None:
            # append _n to the original
            value_number = self.get(ssa.target)
            replaced_str = ssa.target + '_' + str(value_number)

            # change the old str to replaced str
            self.val_num_var_list.remove(ssa.target)
            self.val_num_var_list.insert(value_number, replaced_str)

            self.__setitem__(replaced_str, value_number)
            self.__setitem__(ssa.target, self.current_value)
            self.val_num_var_list.append(ssa.target)
            self.current_value += 1

        else:
            self.val_num_var_list.append(ssa.target)
            self.__setitem__(ssa.target, self.current_value)
            self.current_value += 1

    def get_value_number(self, var):
        """
        return enumerated value number for the var
        :param var:
        :return:
        """
        return self.__getitem__(var)

    def set_value_number(self, var, val_num):
        pass

    def get_variable(self, val_num):
        return self.val_num_var_list[val_num]

    def get_variable_or_constant(self, val_num_list):
        """
        get a variable or constant
        :param val_num_list: [Value Number, operand_type]
        :return: A string if it's variable or a number if it's constant
        """
        if val_num_list[1] == LEFT_OPERATOR_CONSTANT:
            return val_num_list[0]
        else:
            return self.val_num_var_list[val_num_list[0]]


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

    def is_const(self, ssa):
        if is_num(ssa.left_oprd) and ssa.right_oprd is None:
            return True
        return False

    def is_any_oprd_const(self, ssa):
        if is_num(ssa.left_oprd) or is_num(ssa.right_oprd):
            return True
        return False

    def is_both_oprd_const(self, ssa):
        if is_num(ssa.left_oprd) and is_num(ssa.right_oprd):
            return True
        return False

    def identify_oprd(self, ssa_var):
        if ssa_var is not None:
            if ssa_var.is_constant():
                return ssa_var.var
            else:
                return self.variable_dict.get(str(ssa_var))

        else:
            return None

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

    def get_all_lvn_stmt(self, ssa):
        ssa_copy = copy.deepcopy(ssa)
        if ssa_copy.operator is not None:
            yield self.get_lvn_stmt(ssa_copy)
            if not is_num(ssa_copy.left_oprd):
                ssa_copy.left_oprd = self.replace_var(ssa.left_oprd)
                yield self.get_lvn_stmt(ssa_copy)

            if not is_num(ssa_copy.right_oprd):
                if ssa_copy.right_oprd is not None:
                    ssa_copy.right_oprd = self.replace_var(ssa.right_oprd)
                    yield self.get_lvn_stmt(ssa_copy)

        else:
            if not is_num(ssa_copy.left_oprd):
                ssa_copy.left_oprd = self.replace_var(ssa.left_oprd)
            yield self.get_lvn_stmt(ssa_copy)

    def get_lvn_stmt(self, ssa):
        target = self.identify_oprd(ssa.target)
        left_oprd, right_oprd = None, None

        if ssa.left_oprd is not None:
            left_oprd = self.variable_dict.get(str(ssa.left_oprd))

        if ssa.right_oprd is not None:
            right_oprd = self.variable_dict.get(str(ssa.right_oprd))

        lvn_stmt = LvnStatement(target, left_oprd, ssa.operator, right_oprd)
        # lvn_stmt = str(left_oprd) + ssa.operator + str(right_oprd)
        return lvn_stmt

    def add_lvn_stmt(self, lvn_stmt, insert_flag=True):
        """
        add the lvn_stmt into the dict. Modified the tuple
        :param lvn_stmt: a simple expression class
        :return:
        """
        if lvn_stmt.operator is not None:
            if self.get(str(lvn_stmt)) is None:
                if insert_flag is True:
                    self.__setitem__(str(lvn_stmt), [lvn_stmt.target, lvn_stmt.operand_type])
                    self.lvn_code_tuples_list.append_lvn_stmt(lvn_stmt)
                return False
            else:
                # check the operand_type before do the replacing
                list_to_replace = self.get(str(lvn_stmt))
                if list_to_replace[1] == lvn_stmt.operand_type:
                    self.lvn_code_tuples_list.append((lvn_stmt.target, list_to_replace[0],
                                                      None, None, OPERATOR_VARIABLE))
                    self.simple_assign_dict.__setitem__(lvn_stmt.target,
                                                        [list_to_replace[0], lvn_stmt.operand_type])

                    return True
                else:
                    if insert_flag is True:
                        self.lvn_code_tuples_list.append_lvn_stmt(lvn_stmt)
                    return False

        else:
            self.simple_assign_dict.__setitem__(lvn_stmt.target, [lvn_stmt.left, lvn_stmt.operand_type])
            self.lvn_code_tuples_list.append_lvn_stmt(lvn_stmt)
            return True

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

    def is_simple_expr(self):
        if self.operator is None:
            return True
        return False

    def replace_expr(self, stmt_Vn):
        self.left = stmt_Vn
        self.right, self.operator = None, None
