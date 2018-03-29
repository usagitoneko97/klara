class VariableDict(dict):
    def __init__(self, ssa_code=None):
        if ssa_code is None:
            self.enumerate(ssa_code)
        dict.__init__(self)
        pass

    def enumerate(self, ssa):
        pass

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
        pass


class LvnDict(dict):
    def __init__(self, ssa=None):
        # enumerate ssa_code
        if ssa is not None:
            self.variable_dict = VariableDict(ssa)
        self.variable_dict = VariableDict()
        dict.__init__(self)

    def get_simple_expr(self, ssa):
        pass

    def get_var(self, simple_expr_str):
        # perform search on dict, use the value returned to search on variable_dict and return
        pass

    def enumerate(self, ssa):
        self.variable_dict.enumerate(ssa)


class SimpleExpression:
    def __init__(self, left, right, operator):
        self.left = left
        self.right = right
        self.operator = operator

    def __repr__(self):
        return str(self.left) + str(self.operator) + str(self.right)
