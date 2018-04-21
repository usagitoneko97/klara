import unittest
from dominator import DominatorTree
from cfg import Cfg, RawBasicBlock
import ast
import textwrap

ms = textwrap.dedent


class TestDominator(unittest.TestCase):
    def assertDominatorEqual(self, dom_tree, expected_dominator):
        self.assertEqual(len(dom_tree.cfg.block_list), len(expected_dominator))
        for block_num in range(len(dom_tree.cfg.block_list)):
            dom_list = expected_dominator.get(str(block_num))
            self.assertEqual(len(dom_list), len(dom_tree.cfg.block_list[block_num].dominates_list))
            for dom_number in range(len(dom_list)):
                self.assertEqual(dom_tree.cfg.block_list[block_num].dominates_list[dom_number],
                                 dom_tree.cfg.block_list[dom_list[dom_number]])

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