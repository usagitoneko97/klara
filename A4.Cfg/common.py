import ast
from cfg import RawBasicBlock, Cfg


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


def if_stmt_has_else(ast_if_node):
    pass


def is_blocks_same(block1, block2):
    return str(block1) == str(block2)


def build_blocks(*args, block_links):
    block_list = []
    for i in range(len(args)):
        basic_block = RawBasicBlock(args[i][0], args[i][1], args[i][2])

        block_list.append(basic_block)

    for i in range(len(block_links)):
        nxt_block_list = block_links.get(str(i))
        for nxt_block_num in nxt_block_list:
            Cfg.connect_2_blocks(block_list[i], block_list[nxt_block_num])

    return block_list
