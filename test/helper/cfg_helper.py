from klara.core.cfg import BlockList, Cfg, RawBasicBlock
from klara.core.tree_rewriter import AstBuilder


def build_arbitrary_blocks(block_links, code=None, block_type=None):
    # build all block and assume it's in module scope
    block_list = BlockList()
    as_tree_string = ""
    current_line_number = 1
    for i in range(len(block_links)):
        block_name = chr(65 + i)
        if block_type:
            type_instance = block_type.get(block_name)
            if type_instance is not None:
                if type_instance.__name__ == "ParentScopeBlock":
                    basic_block = type_instance(current_line_number, current_line_number, None, scope_name=block_name)
                else:
                    basic_block = type_instance(current_line_number, current_line_number, None)
            else:
                basic_block = RawBasicBlock(current_line_number, current_line_number, None)
        else:
            basic_block = RawBasicBlock(current_line_number, current_line_number, None)
        current_line_number += 1
        basic_block.name = block_name
        block_list.append(basic_block)

        if code is not None:
            ast_stmts = code.get(basic_block.name)  # type: str
            as_tree_string += ast_stmts

    as_tree = AstBuilder().string_build(as_tree_string)
    for i in range(len(block_links)):
        basic_block = block_list[i]
        if code is not None:
            ast_stmts = code.get(basic_block.name)  # type: str
            ast = AstBuilder().string_build(ast_stmts)
            for b in ast.body:
                b.parent = as_tree
            basic_block.ssa_code.code_list = ast.body
            basic_block.end_line += ast_stmts.count("\n") - 1

    for key, value in block_links.items():
        key_block = block_list.get_block_by_name(key)
        for value_block_str in value:
            Cfg.connect_2_blocks(key_block, block_list.get_block_by_name(value_block_str))

    if code is None:
        return block_list
    else:
        return block_list, as_tree
