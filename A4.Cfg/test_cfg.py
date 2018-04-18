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

    def assertBasicBlockEqual(self, basic_block_real, basic_block_expected, recursion_flag=True):
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
                if recursion_flag == True:
                    self.assertBasicBlockEqual(basic_block_real.nxt_block[nxt_block_num],
                                               basic_block_expected.nxt_block[nxt_block_num])
                else:
                    for ast_list_num in range(len(basic_block_real.nxt_block[nxt_block_num].ast_list)):
                        self.assertEqual(basic_block_real.nxt_block[nxt_block_num].ast_list[ast_list_num],
                                         basic_block_expected.nxt_block[nxt_block_num].ast_list[ast_list_num])

    def assertCfgWithAst(self, cfg_real, *args):
        cfg_expected = Cfg()

        # a = 3
        # a = 4
        for ast_list in args:
            basic_block = BasicBlock()
            basic_block.ast_list.extend(ast_list)
            cfg_expected.block_list.append(basic_block)

        self.assertCfgEqual(cfg_real, cfg_expected)

    def assertCfgWithBasicBlocks(self, cfg_real, *args, block_links):
        cfg_expected = Cfg()

        block_list = self.build_blocks(*args, block_links=block_links)
        cfg_expected.block_list.extend(block_list)

        self.assertCfgEqual(cfg_real, cfg_expected)

    @staticmethod
    def fill_nxt_block(cfg_expected, block_links):
        for i in range(len(block_links)):
            nxt_block_list = block_links.get(str(i))
            for nxt_block_num in nxt_block_list:
                cfg_expected.block_list[i].nxt_block.append(cfg_expected.block_list[nxt_block_num])

    @staticmethod
    def build_blocks(*args, block_links):
        block_list = []
        for i in range(len(args)):
            basic_block = BasicBlock()
            basic_block.ast_list.extend(args[i])

            block_list.append(basic_block)

        for i in range(len(block_links)):
            nxt_block_list = block_links.get(str(i))
            for nxt_block_num in nxt_block_list:
                block_list[i].nxt_block.append(block_list[nxt_block_num])

        return block_list

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
            a = 3           # --- 1st
            if a > 3:       # ---  |
                a = 4       # --- 2nd
            else:           # ----3rd
                z = 5       # ---- |
            """)
        )
        cfg_real = Cfg(as_tree)

        self.assertCfgWithBasicBlocks(cfg_real,
                                      as_tree.body[:2],
                                      as_tree.body[1].body[0:1],
                                      as_tree.body[1].orelse[0:1],
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
                                      as_tree.body[:2],
                                      as_tree.body[1].body[0:1],
                                      as_tree.body[1].orelse[0:1],
                                      as_tree.body[2:],
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
                                      as_tree.body[:2],
                                      as_tree.body[1].body[0:1],
                                      as_tree.body[1].orelse[:1],
                                      as_tree.body[1].orelse[0].body,
                                      as_tree.body[2:],
                                      block_links={'0': [1, 2], '1': [4], '2': [3, 4], '3': [4], '4': []}
                                      )

    # --------------------- build while body test--------------------
    def test_build_while_body_given_only_while(self):
        as_tree = ast.parse(ms("""\
            while a < 3:  # 1st block
                z = 4     # 2nd block
            """))

        while_block = BasicBlock(1, ast_list=as_tree.body)
        cfg_handler = Cfg()
        real_tail_list = cfg_handler.build_while_body(while_block)

        expected_block_list = self.build_blocks(as_tree.body,
                                                as_tree.body[0].body,
                                                block_links={'0': [1], '1': [0]})

        self.assertBasicBlockEqual(while_block, expected_block_list[0], recursion_flag=False)
        self.assertBasicBlockEqual(real_tail_list[0], expected_block_list[0], recursion_flag=False)
