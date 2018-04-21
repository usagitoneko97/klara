import copy
import common


class DominatorTree:
    def __init__(self, cfg):
        self.dominator_root = None
        self.dominator_nodes = []
        self.cfg = cfg

    def fill_dominates(self):
        for removed_block_num in (range(len(self.cfg.block_list))):
            root = copy.deepcopy(self.cfg.root)
            dom_block_list = copy.copy(self.cfg.block_list)
            # remove the block
            # walk again
            root = self.cfg.delete_node(root, self.cfg.block_list[removed_block_num])
            for not_dom_block in self.cfg.walk_block(root):
                self.remove_block_from_list(dom_block_list, not_dom_block)

            self.remove_block_from_list(dom_block_list, self.cfg.block_list[removed_block_num])
            self.cfg.block_list[removed_block_num].dominates_list.extend(dom_block_list)

    def remove_block_from_list(self, block_list, block_to_remove):
        for block in block_list:
            if common.is_blocks_same(block, block_to_remove):
                block_list.remove(block)