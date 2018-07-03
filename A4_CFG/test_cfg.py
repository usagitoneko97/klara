import unittest
from .cfg import Cfg, RawBasicBlock, build_blocks, GetBlocks
import ast
import textwrap
from Common import cfg_common
from Common.test_helper.cfg_th import CfgTestCase
ms = textwrap.dedent


class TestCfg(CfgTestCase):
    @staticmethod
    def fill_nxt_block(cfg_expected, block_links):
        for i in range(len(block_links)):
            nxt_block_list = block_links.get(str(i))
            for nxt_block_num in nxt_block_list:
                cfg_expected.block_list[i].nxt_block.append(cfg_expected.block_list[nxt_block_num])


# ------------------get_simple_block----------------------------
    def test_get_simple_block_given_no_indent(self):
        as_tree = ast.parse(ms("""\
            a = 3
            a = 4
            """)
        )
        get_blocks_handler = GetBlocks(as_tree, as_tree.body)
        simple_block_list = []
        for simple_block in get_blocks_handler.get_basic_block():
            simple_block_list.append(simple_block)

        expected_block = RawBasicBlock(start_line=1, end_line=2)

        self.assertBasicBlockEqual(simple_block_list[0], expected_block)

    def test_get_simple_block_given_if(self):
        as_tree = ast.parse(ms("""\
            a = 3
            if a < 3:
                b = 4
            c = 5
            """)
        )
        get_blocks_handler = GetBlocks(as_tree, as_tree.body)
        simple_block_list = []
        for basic_block in get_blocks_handler.get_basic_block():
            simple_block_list.append(basic_block)

        expected_block_0 = RawBasicBlock(start_line=1, end_line=2, block_end_type='If')
        expected_block_1 = RawBasicBlock(start_line=4, end_line=4)

        self.assertBasicBlockEqual(simple_block_list[0], expected_block_0, block_index=0)
        self.assertBasicBlockEqual(simple_block_list[1], expected_block_1, block_index=1)

    def test_get_simple_block_given_while(self):
        as_tree = ast.parse(ms("""\
            a = 3
            while a < 3:
                b = 4
            c = 5
            """)
        )
        get_blocks_handler = GetBlocks(as_tree, as_tree.body)
        simple_block_list = []
        for basic_block in get_blocks_handler.get_basic_block():
            simple_block_list.append(basic_block)

        expected_block_0 = RawBasicBlock(start_line=1, end_line=2, block_end_type='While')
        expected_block_1 = RawBasicBlock(start_line=4, end_line=4)

        self.assertBasicBlockEqual(simple_block_list[0], expected_block_0)
        self.assertBasicBlockEqual(simple_block_list[1], expected_block_1)

    # ----------------- cfg test------------------

    def test_cfg_given_no_branch(self):
        as_tree = ast.parse(ms("""\
            a = 3
            a = 4
            """)
        )
        cfg_real = Cfg(as_tree)

        self.assertCfgWithBasicBlocks(cfg_real,
                                      [1, 2, None],
                                      block_links={})

    def test_cfg_given_if_else_without_link_tail(self):
        as_tree = ast.parse(ms("""\
            a = 3           # 0
            if a > 3:       # 1
                a = 4       # 2
            else:           # 3
                z = 5       # 4
            """)
        )
        cfg_real = Cfg(as_tree)

        self.assertCfgWithBasicBlocks(cfg_real,
                                      [1, 2, 'If'], [3, 3, None], [5, 5, None],
                                      block_links={'0': [1, 2], '1': [], '2': []}
                                      )

    def test_cfg_given_if_else_with_link_tail(self):
        as_tree = ast.parse(ms("""\
            a = 3           # 1st
            if a > 3:       #  |
                a = 4       # 2nd
            else:           # 3rd
                z = 5       #  |
            y = 5           # 4th
            """)
        )
        cfg_real = Cfg(as_tree)

        self.assertCfgWithBasicBlocks(cfg_real,
                                      [1, 2, 'If'], [3, 3, None], [5, 5, None], [6, 6, None],
                                      block_links={'0': [1, 2], '1': [3], '2': [3], '3': []}
                                      )

    def test_cfg_given_if_elif_no_else(self):
        as_tree = ast.parse(ms("""\
            a = 3          #--- 1st
            if a > 3:      #---  |
                a = 4      #--- 2nd
            elif a < 1:    #--- 3rd
                a = 5      #--- 4th
            c = 5          #--- 5th
            """)
        )
        cfg_real = Cfg(as_tree)

        self.assertCfgWithBasicBlocks(cfg_real,
                                      [1, 2, 'If'], [3, 3, None], [4, 4, 'If'], [5, 5, None], [6, 6, None],
                                      block_links={'0': [1, 2], '1': [4], '2': [3, 4], '3': [4], '4': []}
                                      )

    # TODO: test for nested if statement
    # --------------------- build while body test--------------------
    def test_build_while_body_given_only_while(self):
        as_tree = ast.parse(ms("""\
            while a < 3:  # 1st block
                z = 4     # 2nd block
            """))

        while_block = RawBasicBlock(1, 1, 'While')
        cfg_handler = Cfg()
        cfg_handler.as_tree = as_tree
        real_tail_list = cfg_handler.build_while_body(while_block)

        expected_block_list = build_blocks([1, 1, 'While'], [2, 2, None],
                                                block_links={'0': [1], '1': [0]})

        self.assertBasicBlockEqual(while_block, expected_block_list[0])
        self.assertBasicBlockEqual(real_tail_list[0], expected_block_list[0])

    def test_build_while_body_given_body_if(self):
        as_tree = ast.parse(ms("""\
            while a < 3:    # 1st block
                if a < 2:   # 2nd block
                     z = 2  # 3rd block
                b = 2       # 4th block
            """))

        while_block = RawBasicBlock(1, 1, 'While')
        cfg_handler = Cfg()
        cfg_handler.as_tree = as_tree
        real_tail_list = cfg_handler.build_while_body(while_block)

        expected_block_list = build_blocks([1, 1, 'While'], [2, 2, 'If'], [3, 3, None], [4, 4, None],
                                                block_links={'0': [1], '1': [2, 3], '2': [3], '3': [0]})

        self.assertBasicBlockEqual(while_block, expected_block_list[0])
        self.assertBasicBlockEqual(real_tail_list[0], expected_block_list[0])

    def test_cfg_given_while_body_if(self):
        as_tree = ast.parse(ms("""\
            z = 2           # 0th block
            while a < 3:    # 1st block
                if a < 2:   # 2nd block
                     z = 2  # 3rd block
                b = 2       # 4th block
            c = 3           # 5th block
            """))

        cfg_real = Cfg(as_tree)

        self.assertCfgWithBasicBlocks(cfg_real,
                                      [1, 1, None], [2, 2, 'While'], [3, 3, 'If'], [4, 4, None], [5, 5, None], [6, 6, None],
                                      block_links={'0': [1], '1': [2, 5], '2': [3, 4], '3': [4], '4': [1], '5': []})

    # -----------------walk basic_block test---------------
    def test_walk_given_2_block(self):
        as_tree = ast.parse(ms("""\
            z = 2
            if z < 2:
                y = 3
            """))

        cfg_real = Cfg(as_tree)

        blocks_list = []
        for blocks in cfg_common.walk_block(cfg_real.block_list[0]):
            blocks_list.append(blocks)

        expected_block_list = build_blocks([3, 3, None], [1, 2, 'If'],
                                           block_links={'1': [0], '0': []})

        self.assertBasicBlockListEqual(blocks_list, expected_block_list)

    def test_walk_given_recursive_block(self):
        as_tree = ast.parse(ms("""\
             z = 2           # 0th block
             while a < 3:    # 1st block
                 if a < 2:   # 2nd block
                      z = 2  # 3rd block
                 b = 2       # 4th block
             c = 3           # 5th block
             """))

        cfg_real = Cfg(as_tree)
        blocks_list = []
        for blocks in cfg_common.walk_block(cfg_real.block_list[0]):
            blocks_list.append(blocks)

    def test_delete_node(self):
        as_tree = ast.parse(ms("""\
             z = 2           # 0th block
             while a < 3:    # 1st block
                 if a < 2:   # 2nd block
                      z = 2  # 3rd block
                 b = 2       # 4th block
             c = 3           # 5th block
             """))

        cfg_real = Cfg(as_tree)
        cfg_real.root = cfg_common.delete_node(cfg_real.root, RawBasicBlock(1, 1))
