import ast


class VarAst:
    """
    class that extract the variable from the ast statement
    """
    def __init__(self, ast_stmt):
        self.targets_var = []
        self.values_var = []
        self.targets_var, self.values_var = self.get_var_ast(ast_stmt)

    def get_var_ast(self, ast_stmt):
        targets, values = [], []
        if isinstance(ast_stmt, ast.Assign):
            targets, values = self.get_var_ast_assign(ast_stmt)
        elif isinstance(ast_stmt, ast.If) or isinstance(ast_stmt, ast.While):
            targets, values = self.get_var_ast_if_while(ast_stmt)
        return targets, values

    def get_var_ast_bin_op(self, ast_bin_op):
        values = []
        if isinstance(ast_bin_op.left, ast.Name):
            values.append(ast_bin_op.left.id)
        if isinstance(ast_bin_op.right, ast.Name):
            values.append(ast_bin_op.right.id)

        return values

    def get_var_ast_tuple(self, ast_tuple):
        return [value.id for value in ast_tuple.elts]

    def get_var_ast_assign(self, ast_assign):
        targets, values = [], []
        if isinstance(ast_assign.targets[0], ast.Name):
            targets = [ast_assign.targets[0].id]
        else:
            targets = [tar.id for tar in ast_assign.targets[0].elts]

        if isinstance(ast_assign.value, ast.BinOp):
            values = self.get_var_ast_bin_op(ast_assign.value)

        elif isinstance(ast_assign.value, ast.Name):
            values.append(ast_assign.value.id)

        elif isinstance(ast_assign.value, ast.Tuple):
            values = self.get_var_ast_tuple(ast_assign.value)

        return targets, values

    def get_var_ast_compare(self, ast_compare):
        values = []
        if isinstance(ast_compare.left, ast.Name):
            values.append(ast_compare.left.id)

        if isinstance(ast_compare.comparators[0], ast.Name):
            values.append(ast_compare.comparators[0].id)

        return values

    def get_var_ast_if_while(self, ast_if):
        targets, values = [], []
        values = self.get_var_ast_compare(ast_if.test)
        return targets, values
