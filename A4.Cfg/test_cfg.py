import unittest
from cfg import Cfg, BasicBlock
import ast
import textwrap

ms = textwrap.dedent


class test_cfg(unittest.TestCase):
    def assertCfgEqual(self, cfg_real, cfg_expected):
        self.assertEqual(len(cfg_real.block_list), len(cfg_expected.block_list),
                         "Number of real basic block {} is not the same as expected {}".format(len(cfg_real.block_list),
                                                                                 len(cfg_expected.block_list))
                         )
        for block_list_num in range(len(cfg_real.block_list)):
            self.assertBasicBlockEqual(cfg_real.block_list[block_list_num],
                                       cfg_expected.block_list[block_list_num])

    def assertBasicBlockEqual(self, basic_block_real, basic_block_expected):
        self.assertEqual(len(basic_block_real.ast_list), len(basic_block_expected.ast_list),
                         "Number of ast stmt {} is not the same as expected {}".format(len(basic_block_real.ast_list),
                                                                                 len(basic_block_expected.ast_list))
                         )

        for ast_list_num in range(len(basic_block_real.ast_list)):
            self.assertEqual(basic_block_real.ast_list[ast_list_num],
                             basic_block_expected.ast_list[ast_list_num])

            # ---- checking of next block-----------
            self.assertEqual(len(basic_block_real.nxt_block), len(basic_block_expected.nxt_block),
                             'number of next block of real is not the same as expected')

            for nxt_block_num in range(len(basic_block_real.nxt_block)):
                self.assertBasicBlockEqual(basic_block_real.nxt_block[nxt_block_num],
                                           basic_block_expected.nxt_block[nxt_block_num])

    def assertCfgWithAst(self, cfg_real, *args):
        cfg_expected = Cfg()

        # a = 3
        # a = 4
        for ast_list in args:
            basic_block = BasicBlock()
            basic_block.ast_list.extend(ast_list)
            cfg_expected.block_list.append(basic_block)

        self.assertCfgEqual(cfg_real, cfg_expected)

# ------------------link_tail_to_cur_block --------------------
    def test_link_tail_to_cur_block_given_1_tail(self):

        pass

# ------------------get_simple_block----------------------------
    def test_get_simple_block_given_no_indent(self):
        as_tree = ast.parse(ms("""\
            a = 3
            a = 4
            """)
        )
        cfg_holder = Cfg()
        simple_block_list = []
        for simple_block in cfg_holder.get_basic_block(as_tree.body):
            simple_block_list.append(simple_block)

        expected_block = BasicBlock()
        expected_block.ast_list.extend(as_tree.body)

        self.assertBasicBlockEqual(simple_block_list[0], expected_block)

    def test_get_simple_block_given_indent(self):
        as_tree = ast.parse(ms("""\
            a = 3
            if a < 3:
                b = 4
            c = 5
            """)
        )
        cfg_holder = Cfg()
        simple_block_list = []
        for basic_block in cfg_holder.get_basic_block(as_tree.body):
            simple_block_list.append(basic_block)

        expected_block_0 = BasicBlock()
        expected_block_0.ast_list.extend(as_tree.body[:2])

        expected_block_1 = BasicBlock()
        expected_block_1.ast_list.extend(as_tree.body[2:])

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

        self.assertCfgWithAst(cfg_real, as_tree.body)
        pass

    def test_cfg_given_if_else_without_link_tail(self):
        as_tree = ast.parse(ms("""\
            a = 3
            if a > 3:
                a = 4
            else:
                z = 5
            """)
        )
        cfg_real = Cfg(as_tree)

        b_block_0 = BasicBlock(0, as_tree.body[:2])
        b_block_1 = BasicBlock(1, as_tree.body[1].body[0:1])
        b_block_2 = BasicBlock(2, as_tree.body[1].orelse[0:1])

        b_block_0.nxt_block.insert(BasicBlock.IS_TRUE_BLOCK, b_block_1)
        b_block_0.nxt_block.insert(BasicBlock.IS_FALSE_BLOCK, b_block_2)

        cfg_expected = Cfg(None, b_block_0, b_block_1, b_block_2)
        self.assertCfgEqual(cfg_real, cfg_expected)

    def test_cfg_given_if_else_with_link_tail(self):
        as_tree = ast.parse(ms("""\
            a = 3
            if a > 3:
                a = 4
            else:
                z = 5
            y = 5
            """)
        )
        cfg_real = Cfg(as_tree)

        b_block_0 = BasicBlock(0, as_tree.body[:2])
        b_block_1 = BasicBlock(1, as_tree.body[1].body[0:1])
        b_block_2 = BasicBlock(2, as_tree.body[1].orelse[0:1])
        b_block_3 = BasicBlock(2, as_tree.body[2:])

        b_block_0.nxt_block.insert(BasicBlock.IS_TRUE_BLOCK, b_block_1)
        b_block_0.nxt_block.insert(BasicBlock.IS_FALSE_BLOCK, b_block_2)

        b_block_1.nxt_block.insert(BasicBlock.IS_TRUE_BLOCK, b_block_3)
        b_block_2.nxt_block.insert(BasicBlock.IS_TRUE_BLOCK, b_block_3)

        cfg_expected = Cfg(None, b_block_0, b_block_1, b_block_2, b_block_3)
        self.assertCfgEqual(cfg_real, cfg_expected)

    def test_cfg_given_if_elif_no_else(self):
        as_tree = ast.parse(ms("""\
            a = 3
            a = 4
            if a > 3:
                a = 4
            elif a < 1:
                a = 5
            c = 5
            """)
        )
        cfg = Cfg(as_tree)
        pass
