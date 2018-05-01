from cfg import BlockList, RawBasicBlock, Cfg


def build_blocks_arb(block_links):
    block_list = BlockList()
    for i in range(len(block_links)):
        basic_block = RawBasicBlock(i, i, None)
        basic_block.name = chr(65 + i)
        block_list.append(basic_block)

    for key, value in block_links.items():
        key_block = block_list.get_block_by_name(key)
        for value_block_str in value:
            Cfg.connect_2_blocks(key_block, block_list.get_block_by_name(value_block_str))

    return block_list

