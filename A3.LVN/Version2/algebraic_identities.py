class AlgIdent:
    def __init__(self):
        self.alg_ident_dict = {'Add': self.alg_ident_add, 'Sub': self.alg_ident_sub,
                               'Mult': self.alg_ident_mult, 'Div': self.alg_ident_div}

    def alg_ident_div(self, left, right):
        if right == 1:
            return left, None, None
        elif left == right:
            return 1, None, None
        elif left == 0:
            return 0, None, None
        else:
            return left, 'Div', right

    def alg_ident_mult(self, left, right):
        if left == 1:
            return right, None, None
        elif right == 1:
            return left, None, None
        elif left == 0 or right == 0:
            return 0, None, None
        else:
            return left, 'Mult', right

    def alg_ident_add(self, left, right):
        if left == 0:
            return right, None, None
        elif right == 0:
            return left, None, None
        elif left == right:
            return 2, 'Mult', right
        else:
            return left, 'Add', right
        pass

    def alg_ident_sub(self, left, right):
        if left == right:
            return 0, None, None
        elif right == 0:
            return left, None, None
        else:
            return left, 'Sub', right
        pass

    def find_operands_func(self, operand_str):
        return self.alg_ident_dict[operand_str]

    def optimize_alg_identities(self, left, op, right):
        if op is None:
            return None
        else:
            # find respective func through this dict
            op_func = self.find_operands_func(op)
            left, op, right = op_func(left, right)
            return left, op, right
