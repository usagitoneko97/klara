import copy
import common
from cfg import Cfg, RawBasicBlock


class DominatorNodesList(list):
    def get_block(self, block_to_find):
        for block in self.__iter__():
            if common.is_blocks_same(block, block_to_find):
                return block


class DominatorTree:
    def __init__(self, cfg):
        self.dominator_root = None
        self.dominator_nodes = DominatorNodesList()
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

    def build_tree(self):
        # TODO: clarify the code below
        for block_in_cfg in self.cfg.walk_block(self.cfg.root):
            block_in_dom_list = RawBasicBlock(block_in_cfg.start_line, block_in_cfg.end_line)
            self.dominator_nodes.append(block_in_dom_list)
            for dom_block in block_in_cfg.dominates_list:
                dom_block_in_list = self.dominator_nodes.get_block(dom_block)
                if not dom_block_in_list.prev_block_list:
                    Cfg.connect_2_blocks(block_in_dom_list, dom_block_in_list)

        self.dominator_root = self.dominator_nodes[-1]

    def fill_df(self):
        for nodes in self.cfg.block_list:
            if nodes.get_num_of_parents() > 1:
                for pred_node in nodes.prev_block_list:
                    runner = pred_node
                    while not common.is_blocks_same(self.dominator_nodes.get_block(runner),
                                                    self.get_idom(nodes)) \
                            and runner is not None:
                        runner.df = nodes
                        runner = self.get_idom(runner)

    def get_idom(self, cfg_node):
        dom_node = self.dominator_nodes.get_block(cfg_node)
        if dom_node.prev_block_list:
            cfg_idom_node = self.cfg.find_node(dom_node.prev_block_list[0])
            return cfg_idom_node
        return None

