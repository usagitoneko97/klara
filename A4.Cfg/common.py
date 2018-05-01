import ast

import textwrap
ms = textwrap.dedent

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
    if block1.start_line == block2.start_line and \
            block1.end_line == block2.end_line:
        return True
    return False


def walk_block(basic_block):
    walk_record = []
    yield from _walk_block(walk_record, basic_block)


def _walk_block(walk_record, basic_block):
    """
    yield nodes from bottom
    :return:
    """
    if basic_block is None:
        return
    walk_record.append(basic_block)
    for next_block in basic_block.nxt_block_list:
        if next_block not in walk_record and next_block is not None:
            yield from _walk_block(walk_record, next_block)
    yield basic_block


def delete_node(root, block_to_delete):
    delete_record = []
    root = _delete_node(delete_record, root, block_to_delete)
    return root


def _delete_node(delete_record, root,  block_to_delete):
    if is_blocks_same(root, block_to_delete) or root is None:
        return None

    delete_record.append(root)
    for next_block_num in range(len(root.nxt_block_list)):
        if root.nxt_block_list[next_block_num] not in delete_record:
            root.nxt_block_list[next_block_num] = _delete_node(delete_record,
                                                               root.nxt_block_list[next_block_num],
                                                               block_to_delete)

    # no child left, return yourself
    return root


def find_node(block_list, block_to_find):
    for block in block_list:
        if is_blocks_same(block, block_to_find):
            return block
    return None


def remove_block_from_list(block_list, block_to_remove):
    for block in block_list:
        if is_blocks_same(block, block_to_remove):
            block_list.remove(block)
