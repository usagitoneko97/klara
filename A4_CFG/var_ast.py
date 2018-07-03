import ast


class VarAst:
    """
    class that extract the variable from the ast statement
    """
    def __init__(self, ast_stmt):
        self.ast_stmt = ast_stmt
        self.left_operand, self.right_operand = None, None
        self.targets_var = []
        self.values_var = []
        self.targets_var, self.values_var, self.target_op, self.body_op = self.get_var_ast(ast_stmt)

    def get_target(self):
        return self.targets_var[0] if len(self.targets_var) != 0 else None

    def get_var_ast(self, ast_stmt):
        targets, values = [], []
        target_op = ast_stmt.__class__.__name__
        body_op = None

        if isinstance(ast_stmt, ast.Assign):
            targets, values, body_op = self.get_var_ast_assign(ast_stmt)
        elif isinstance(ast_stmt, ast.If) or isinstance(ast_stmt, ast.While):
            targets, values, body_op = self.get_var_ast_if_while(ast_stmt)
        elif isinstance(ast_stmt, ast.Return):
            targets, values, body_op = self.get_var_ast_return(ast_stmt)

        return targets, values, target_op, body_op

    def get_var_ast_bin_op(self, ast_bin_op):
        values = []
        if isinstance(ast_bin_op.left, ast.Name):
            values.append(ast_bin_op.left.id)
            self.left_operand = ast_bin_op.left.id

        elif isinstance(ast_bin_op.left, ast.Num):
            self.left_operand = ast_bin_op.left.n

        if isinstance(ast_bin_op.right, ast.Name):
            values.append(ast_bin_op.right.id)
            self.right_operand = ast_bin_op.right.id

        elif isinstance(ast_bin_op.right, ast.Num):
            self.right_operand = ast_bin_op.right.n

        return values, ast_bin_op.op.__class__.__name__

    def get_var_ast_tuple(self, ast_tuple):
        return [value.id for value in ast_tuple.elts]

    def get_var_ast_assign(self, ast_assign):
        targets, body_op, values = [], None, []
        if isinstance(ast_assign.targets[0], ast.Name):
            targets = [ast_assign.targets[0].id]
        else:
            targets = [tar.id for tar in ast_assign.targets[0].elts]

        if isinstance(ast_assign.value, ast.BinOp):
            values, body_op = self.get_var_ast_bin_op(ast_assign.value)

        elif isinstance(ast_assign.value, ast.Name):
            self.left_operand = ast_assign.value.id
            values.append(ast_assign.value.id)

        elif isinstance(ast_assign.value, ast.Tuple):
            values = self.get_var_ast_tuple(ast_assign.value)

        elif isinstance(ast_assign.value, ast.Num):
            self.left_operand = ast_assign.value.n

        elif isinstance(ast_assign.value, ast.UnaryOp):
            values, body_op = self.get_var_ast_unary_op(ast_assign.value)

        elif isinstance(ast_assign.value, ast.Compare):
            values, body_op = self.get_var_ast_compare(ast_assign.value)

        return targets, values, body_op

    def get_var_ast_compare(self, ast_compare):
        values = []
        if isinstance(ast_compare.left, ast.Name):
            values.append(ast_compare.left.id)
            self.left_operand = ast_compare.left.id

        elif isinstance(ast_compare.left, ast.Num):
            self.left_operand = ast_compare.left.n

        if isinstance(ast_compare.comparators[0], ast.Name):
            self.right_operand = ast_compare.comparators[0].id
            values.append(ast_compare.comparators[0].id)
            
        elif isinstance(ast_compare.comparators[0], ast.Num):
            self.right_operand = ast_compare.comparators[0].n

        return values, ast_compare.ops[0].__class__.__name__

    def get_var_ast_if_while(self, ast_if):
        targets, values = [], []
        values, op = self.get_var_ast_compare(ast_if.test)
        return targets, values, op

    def get_var_ast_unary_op(self, ast_unary):
        values = []
        if isinstance(ast_unary.operand, ast.Name):
            values.append(ast_unary.operand.id)
            self.right_operand = ast_unary.operand.id

        elif isinstance(ast_unary.operand, ast.Num):
            self.right_operand = ast_unary.operand.n

        return values, ast_unary.op.__class__.__name__

    def get_var_ast_return(self, ast_return):
        values = []
        body_op = None
        if isinstance(ast_return.value, ast.Name):
            self.left_operand = ast_return.value.id
            values.append(ast_return.value.id)
        elif isinstance(ast_return.value, ast.Num):
            self.left_operand = ast_return.value.n
            values.append(ast_return.value.n)
        elif isinstance(ast_return.value, ast.BinOp):
            values, body_op = self.get_var_ast_bin_op(ast_return.value)

        return [], values, body_op





