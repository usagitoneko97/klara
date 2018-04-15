import ast


def is_call_func(ast_node):
    if isinstance(ast_node, ast.Expr):
        if isinstance(ast_node.value, ast.Call):
            return True
    return False


def is_if_stmt(ast_node):
    if isinstance(ast_node, ast.If):
        return True
    return False

def if_stmt_has_else(ast_if_node):
    pass