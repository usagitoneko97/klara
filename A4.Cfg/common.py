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


def is_while_stmt(ast_node):
    if isinstance(ast_node, ast.While):
        return True
    return False


def is_blocks_same(block1, block2):
    return str(block1) == str(block2)
