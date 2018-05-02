from cfg import BlockList, RawBasicBlock, Cfg


def build_blocks_arb(block_links, code=None):
    block_list = BlockList()
    as_tree_string = ""
    current_line_number = 1
    for i in range(len(block_links)):
        basic_block = RawBasicBlock(current_line_number, current_line_number, None)
        basic_block.name = chr(65 + i)
        block_list.append(basic_block)

        if code is not None:
            ast_stmts = code.get(basic_block.name)
            as_tree_string += ast_stmts
            basic_block.end_line += (ast_stmts.count("\n") -1)
            current_line_number = basic_block.end_line + 1

    for key, value in block_links.items():
        key_block = block_list.get_block_by_name(key)
        for value_block_str in value:
            Cfg.connect_2_blocks(key_block, block_list.get_block_by_name(value_block_str))

    if code is None:
        return block_list
    else:
        return block_list, as_tree_string

