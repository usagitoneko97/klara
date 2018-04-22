import unittest
from dominator import DominatorTree
from cfg import Cfg, build_blocks, RawBasicBlock
import ast
import textwrap
import common

ms = textwrap.dedent


class TestDominator(unittest.TestCase):
    def assertDfEqual(self, dom_tree_real, *expected_df):
        for df_block_num in range(len(expected_df)):
            self.assertEqual(len(dom_tree_real.cfg.block_list), len(expected_df))
            if len(expected_df[df_block_num]) == 0:
                self.assertIsNone(dom_tree_real.cfg.block_list[df_block_num].df)
            else:
                self.assertTrue(common.is_blocks_same(RawBasicBlock(expected_df[df_block_num][0],
                                                                    expected_df[df_block_num][1]),
                                                      dom_tree_real.cfg.block_list[df_block_num].df))

    def assertDominatorEqual(self, dom_tree, expected_dominator):
        self.assertEqual(len(dom_tree.cfg.block_list), len(expected_dominator))
        for block_num in range(len(dom_tree.cfg.block_list)):
            dom_list = expected_dominator.get(str(block_num))
            self.assertEqual(len(dom_list), len(dom_tree.cfg.block_list[block_num].dominates_list))
            for dom_number in range(len(dom_list)):
                self.assertEqual(dom_tree.cfg.block_list[block_num].dominates_list[dom_number],
                                 dom_tree.cfg.block_list[dom_list[dom_number]])

    def assertBasicBlockEqual(self, basic_block_real, basic_block_expected, block_index=0):

        self.assertEqual(basic_block_real.block_end_type, basic_block_expected.block_end_type)

        self.assertStartEnd([basic_block_real.start_line, basic_block_real.end_line],
                            [basic_block_expected.start_line, basic_block_expected.end_line],
                            block_index)

        for nxt_block_num in range(len(basic_block_real.nxt_block_list)):
            self.assertStartEnd([basic_block_real.nxt_block_list[nxt_block_num].start_line,
                                 basic_block_real.nxt_block_list[nxt_block_num].start_line],
                                [basic_block_expected.nxt_block_list[nxt_block_num].end_line,
                                 basic_block_expected.nxt_block_list[nxt_block_num].end_line],
                                block_index,
                                nxt_or_prev='next')

    def assertStartEnd(self, real_block, expected_block, block_index, nxt_or_prev=''):
        self.assertEqual(real_block[0], expected_block[0],
                         'On block {}, the start line is not the same at {}'.format(block_index, nxt_or_prev))

        self.assertEqual(real_block[1], expected_block[1],
                         'On block {}, the end line is not the same at {}'.format(block_index, nxt_or_prev))

    def assertBasicBlockListEqual(self, block_real, block_expected):
        self.assertEqual(len(block_real), len(block_expected), 'the len of basic block is not the same')
        for block_num in range(len(block_real)):
            self.assertBasicBlockEqual(block_real[block_num], block_expected[block_num],
                                       block_index=block_num)

    def test_fill_dominate_given_if_else(self):
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
        dom_tree = DominatorTree(cfg_real)
        dom_tree.fill_dominates()
        expected_dominator = {'0': [1, 2, 3],
                              '1': [],
                              '2': [],
                              '3': []}

        self.assertDominatorEqual(dom_tree, expected_dominator)

    def test_fill_dominate_given_while(self):
        as_tree = ast.parse(ms("""\
             z = 2           # 0th block
             while a < 3:    # 1st block
                 if a < 2:   # 2nd block
                      z = 2  # 3rd block
                 b = 2       # 4th block
             c = 3           # 5th block
            """)
                            )
        cfg_real = Cfg(as_tree)
        dom_tree = DominatorTree(cfg_real)
        dom_tree.fill_dominates()
        expected_dominator = {'0': [1, 2, 3, 4, 5],
                              '1': [2, 3, 4, 5],
                              '2': [3, 4],
                              '3': [],
                              '4': [],
                              '5': []}

        self.assertDominatorEqual(dom_tree, expected_dominator)

    # -------------- test build dominator tree----------------
    def test_build_dominator_tree_given_1_lvl(self):
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
        dom_tree = DominatorTree(cfg_real)
        dom_tree.fill_dominates()
        dom_tree.build_tree()

        expected_block_list = build_blocks([6, 6, None], [3, 3, None],
                                           [5, 5, None], [1, 2, None],
                                           block_links={'3': [1, 2, 0], '2': [],
                                                        '1': [], '0': []})

        self.assertBasicBlockListEqual(dom_tree.dominator_nodes, expected_block_list)

    def test_build_dominator_tree_given_2_lvl(self):
        as_tree = ast.parse(ms("""\
             z = 2           # 0th block
             while a < 3:    # 1st block
                 if a < 2:   # 2nd block
                      z = 2  # 3rd block
                 b = 2       # 4th block
             c = 3           # 5th block
            """)
                            )
        cfg_real = Cfg(as_tree)
        dom_tree = DominatorTree(cfg_real)
        dom_tree.fill_dominates()
        dom_tree.build_tree()

        expected_block_list = build_blocks([5, 5, None], [4, 4, None], [3, 3, None],
                                           [6, 6, None], [2, 2, None], [1, 1, None],
                                           block_links={'5': [4], '4': [2, 3], '2': [1, 0],
                                                        '1': [], '0': [], '3': []})
        
        self.assertBasicBlockListEqual(dom_tree.dominator_nodes, expected_block_list)
        pass

    def test_fill_df_given_if_else(self):
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
        dom_tree = DominatorTree(cfg_real)
        dom_tree.fill_dominates()
        dom_tree.build_tree()
        dom_tree.fill_df()

        self.assertDfEqual(dom_tree, [], [6, 6], [6, 6], [])

    def test_fill_df_given_while(self):
        as_tree = ast.parse(ms("""\
             z = 2           # 0th block
             while a < 3:    # 1st block
                 if a < 2:   # 2nd block
                      z = 2  # 3rd block
                 b = 2       # 4th block
             c = 3           # 5th block
            """)
                            )
        cfg_real = Cfg(as_tree)
        dom_tree = DominatorTree(cfg_real)
        dom_tree.fill_dominates()
        dom_tree.build_tree()
        dom_tree.fill_df()

        self.assertDfEqual(dom_tree, [], [2, 2], [2, 2], [5, 5], [2, 2], [],)
