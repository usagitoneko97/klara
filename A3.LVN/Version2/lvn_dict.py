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
        if not ssa_var.is_constant():
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
    def append_alg_expr(self, alg_expr):
        self.append((alg_expr.target, alg_expr.left, alg_expr.operator,
                     alg_expr.right, alg_expr.operand_type))


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
        self.simple_assign_dict = dict()
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

    def get_all_alg_expr(self, ssa):
        ssa_copy = copy.deepcopy(ssa)
        if ssa_copy.operator is not None:
            yield self.get_alg_expr(ssa_copy)
            if not is_num(ssa_copy.left_oprd):
                ssa_copy.left_oprd = self.replace_var(ssa.left_oprd)
                yield self.get_alg_expr(ssa_copy)

            if not is_num(ssa_copy.right_oprd):
                if ssa_copy.right_oprd is not None:
                    ssa_copy.right_oprd = self.replace_var(ssa.right_oprd)
                    yield self.get_alg_expr(ssa_copy)

        else:
            if not is_num(ssa_copy.left_oprd):
                ssa_copy.left_oprd = self.replace_var(ssa.left_oprd)
            yield self.get_alg_expr(ssa_copy)

    def get_alg_expr(self, ssa):
        operand_type = 0
        target = self.identify_oprd(ssa.target)
        left_oprd, right_oprd = None, None

        if ssa.left_oprd is not None:
            left_oprd = self.identify_oprd(ssa.left_oprd)
            if ssa.left_oprd.is_constant():
                operand_type = 1

        if ssa.right_oprd is not None:
            right_oprd = self.identify_oprd(ssa.right_oprd)
            if ssa.right_oprd.is_constant():
                operand_type = 2

        alg_expr = AlgebraicExpression(left_oprd, right_oprd, ssa.operator, target, operand_type)
        # alg_expr = str(left_oprd) + ssa.operator + str(right_oprd)
        return alg_expr

    def add_alg_expr(self, alg_expr, insert_flag=True):
        """
        add the alg_expr into the dict. Modified the tuple
        :param alg_expr: a simple expression class
        :return:
        """
        if alg_expr.operator is not None:
            if self.get(str(alg_expr)) is None:
                if insert_flag is True:
                    self.__setitem__(str(alg_expr), [alg_expr.target, alg_expr.operand_type])
                    self.lvn_code_tuples_list.append_alg_expr(alg_expr)
                return False
            else:
                # check the operand_type before do the replacing
                list_to_replace = self.get(str(alg_expr))
                if list_to_replace[1] == alg_expr.operand_type:
                    self.lvn_code_tuples_list.append((alg_expr.target, list_to_replace[0],
                                                      None, None, OPERATOR_VARIABLE))
                    self.simple_assign_dict.__setitem__(alg_expr.target,
                                                        [list_to_replace[0], alg_expr.operand_type])

                    return True
                else:
                    if insert_flag is True:
                        self.lvn_code_tuples_list.append_alg_expr(alg_expr)
                    return False

        else:
            self.simple_assign_dict.__setitem__(alg_expr.target, [alg_expr.left, alg_expr.operand_type])
            self.lvn_code_tuples_list.append_alg_expr(alg_expr)
            return True

    def get_var(self, alg_expr_str):
        # perform search on dict, use the value returned to search on variable_dict and return
        pass

    def find_substitute(self, alg_expr):
        pass


class AlgebraicExpression:
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

