from common import *
import copy

class VariableDict(dict):
    def __init__(self, ssa_code=None):
        self.current_value = 0
        self.val_num_var_list = []
        if ssa_code is not None:
            self.enumerate_rhs(ssa_code)
        dict.__init__(self)

    def _add_to_variable_dict(self, string):
        if not is_num(string):
            if string not in self.__repr__():
                self.__setitem__(string, self.current_value)
                self.val_num_var_list.append(string)
                self.current_value += 1

    def enumerate_rhs(self, ssa):
        if ssa.left_oprd is not None:
            self._add_to_variable_dict(ssa.left_oprd)

        if ssa.right_oprd is not None:
            self._add_to_variable_dict(ssa.right_oprd)

    def enumerate_lhs(self, ssa):
        if ssa.target in self.__repr__():
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
        pass

    def set_value_number(self, var, val_num):
        pass

    def get_variable(self, val_num):
        return self.val_num_var_list[val_num]


class LvnDict(dict):
    def __init__(self, ssa=None):
        # enumerate ssa_code
        if ssa is not None:
            self.variable_dict = VariableDict(ssa)
        self.variable_dict = VariableDict()
        self.simple_assign_dict = dict()
        self.lvn_code_tuples_list = []
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

    def identify_oprd(self, oprd):
        if oprd is not None:
            if is_num(oprd):
                return oprd
            else:
                return self.variable_dict.get(oprd)

        else:
            return None

    def get_all_simple_expr(self, ssa):
        ssa_copy = copy.deepcopy(ssa)
        if ssa_copy.operator is not None:
            yield self.get_simple_expr(ssa_copy)
            if not is_num(ssa_copy.left_oprd):
                if self.variable_dict[ssa_copy.left_oprd] in self.simple_assign_dict:
                    simple_assign_list = self.simple_assign_dict[self.variable_dict[ssa_copy.left_oprd]]
                    left_oprd_val_num = simple_assign_list[0]
                    if simple_assign_list[1] != LEFT_OPERATOR_CONSTANT:
                        ssa_copy.left_oprd = self.variable_dict.get_variable(left_oprd_val_num)
                    else:
                        ssa_copy.left_oprd = left_oprd_val_num
                    yield self.get_simple_expr(ssa_copy)

            if not is_num(ssa_copy.right_oprd):
                if ssa_copy.right_oprd is not None:
                    if self.variable_dict[ssa_copy.right_oprd] in self.simple_assign_dict:
                        simple_assign_list = self.simple_assign_dict[self.variable_dict[ssa_copy.right_oprd]]
                        right_oprd_val_num = simple_assign_list[0]
                        if simple_assign_list[1] == NO_OPERATOR_CONSTANT:
                            ssa_copy.right_oprd = self.variable_dict.get_variable(right_oprd_val_num)
                        else:
                            ssa_copy.right_oprd = right_oprd_val_num
                        yield self.get_simple_expr(ssa_copy)

        else:
            if not is_num(ssa_copy.left_oprd):
                if self.variable_dict[ssa_copy.left_oprd] in self.simple_assign_dict:
                    # replacement
                    value_number_to_replace_list = self.simple_assign_dict[self.variable_dict[ssa_copy.left_oprd]]
                    left_oprd_val_num = value_number_to_replace_list[0]
                    if value_number_to_replace_list[1] != LEFT_OPERATOR_CONSTANT:
                        ssa_copy.left_oprd = self.variable_dict.get_variable(left_oprd_val_num)
                    else:
                        ssa_copy.left_oprd = left_oprd_val_num

            yield self.get_simple_expr(ssa_copy)

    def get_simple_expr(self, ssa):
        operand_type = 0
        target = self.variable_dict.current_value
        left_oprd, right_oprd = None, None

        '''
        if self.is_both_oprd_const(ssa):
            # fold
            eval()
        else:
            pass
        '''

        if ssa.left_oprd is not None:
            left_oprd = self.identify_oprd(ssa.left_oprd)
            if is_num(ssa.left_oprd):
                operand_type = 1

        if ssa.right_oprd is not None:
            right_oprd = self.identify_oprd(ssa.right_oprd)
            if is_num(ssa.right_oprd):
                operand_type = 2

        simple_expr = SimpleExpression(left_oprd, right_oprd, ssa.operator, target, operand_type)
        # simple_expr = str(left_oprd) + ssa.operator + str(right_oprd)
        return simple_expr

    def add_simple_expr(self, simple_expr, insert_flag=True):
        """
        add the simple_expr into the dict. Modified the tuple
        :param simple_expr: a simple expression class
        :return:
        """
        if simple_expr.operator is not None:
            if self.get(str(simple_expr)) is None:
                if insert_flag is True:
                    self.__setitem__(str(simple_expr), [simple_expr.target, simple_expr.operand_type])
                    self.lvn_code_tuples_list.append((simple_expr.target, simple_expr.left, simple_expr.operator,
                                                      simple_expr.right, simple_expr.operand_type))
                return False
            else:
                # check the operand_type before do the replacing
                list_to_replace = self.get(str(simple_expr))
                if list_to_replace[1] == simple_expr.operand_type:
                    self.lvn_code_tuples_list.append((simple_expr.target, list_to_replace[0],
                                                      None, None, NO_OPERATOR_CONSTANT))
                    self.simple_assign_dict.__setitem__(simple_expr.target,
                                                        [list_to_replace[0], simple_expr.operand_type])

                    return True
                else:
                    if insert_flag is True:
                        self.lvn_code_tuples_list.append((simple_expr.target, simple_expr.left, simple_expr.operator,
                                                          simple_expr.right, simple_expr.operand_type))
                    return False


        else:
            self.simple_assign_dict.__setitem__(simple_expr.target, [simple_expr.left, simple_expr.operand_type])
            self.lvn_code_tuples_list.append((simple_expr.target, simple_expr.left,
                                              None, None, simple_expr.operand_type))
            return True

    def get_var(self, simple_expr_str):
        # perform search on dict, use the value returned to search on variable_dict and return
        pass

    def enumerate_lhs(self, ssa):
        self.variable_dict.enumerate_lhs(ssa)

    def enumerate_rhs(self, ssa):
        self.variable_dict.enumerate_rhs(ssa)


class SimpleExpression:
    def __init__(self, left, right, operator, target=0, operand_type=0):
        self.left = left
        self.right = right
        self.operator = operator
        self.target = target
        self.operand_type = operand_type

    def __repr__(self):
        if self.operator is None:
            return str(self.left)
        return str(self.left) + self.operator + str(self.right)
