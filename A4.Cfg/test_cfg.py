import unittest
from cfg import Cfg, RawBasicBlock, build_blocks
import ast
import textwrap
import common

ms = textwrap.dedent


class TestCfg(unittest.TestCase):
    def assertCfgEqual(self, cfg_real, cfg_expected):
        self.assertEqual(len(cfg_real.block_list), len(cfg_expected.block_list),
                         "Number of real basic block {} is not the same as expected {}".format(len(cfg_real.block_list),
                                                                                 len(cfg_expected.block_list))
                         )
        for block_list_num in range(len(cfg_real.block_list)):
            self.assertBasicBlockEqual(cfg_real.block_list[block_list_num],
                                       cfg_expected.block_list[block_list_num],
                                       block_index=block_list_num)

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

    def assertBasicBlockListEqual(self, block_real, block_expected):
        self.assertEqual(len(block_real), len(block_expected), 'the len of basic block is not the same')
        for block_num in range(len(block_real)):
            self.assertBasicBlockEqual(block_real[block_num], block_expected[block_num],
                                       block_index=block_num)

    def assertStartEnd(self, real_block, expected_block, block_index, nxt_or_prev=''):
        self.assertEqual(real_block[0], expected_block[0],
                         'On block {}, the start line is not the same at {}'.format(block_index, nxt_or_prev))

        self.assertEqual(real_block[1], expected_block[1],
                         'On block {}, the end line is not the same at {}'.format(block_index, nxt_or_prev))

    def assertCfgWithAst(self, cfg_real, *args):
        cfg_expected = Cfg()

        # a = 3
        # a = 4
        for ast_list in args:
            basic_block = RawBasicBlock()
            basic_block.ast_list.extend(ast_list)
            cfg_expected.block_list.append(basic_block)

        self.assertCfgEqual(cfg_real, cfg_expected)

    def assertCfgWithBasicBlocks(self, cfg_real, *args, block_links):
        cfg_expected = Cfg()

        block_list = build_blocks(*args, block_links=block_links)
        cfg_expected.block_list.extend(block_list)

        self.assertCfgEqual(cfg_real, cfg_expected)

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
        cfg_holder = Cfg()
        simple_block_list = []
        for simple_block in cfg_holder.get_basic_block(as_tree.body):
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
        cfg_holder = Cfg()
        simple_block_list = []
        for basic_block in cfg_holder.get_basic_block(as_tree.body):
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
        cfg_holder = Cfg()
        simple_block_list = []
        for basic_block in cfg_holder.get_basic_block(as_tree.body):
            simple_block_list.append(basic_block)

        expected_block_0 = RawBasicBlock(start_line=1, end_line=2, block_end_type='While')
        expected_block_1 = RawBasicBlock(start_line=4, end_line=4)

        self.assertBasicBlockEqual(simple_block_list[0], expected_block_0)
        self.assertBasicBlockEqual(simple_block_list[1], expected_block_1)

    # ----------------- get ast node test---------------
    def test_get_ast_node_given_2_assign(self):
        as_tree = ast.parse(ms("""\
                    a = 3
                    a = 4
                    """)
                            )

        cfg_real = Cfg()
        node = cfg_real.get_ast_node(as_tree, 2)

        self.assertEqual(node, as_tree.body[1])

    def test_get_ast_node_given_if(self):
        as_tree = ast.parse(ms("""\
                    a = 3
                    if a < 3:
                        z = 2
                    a = 4
                    """)
                            )

        cfg_real = Cfg()
        node = cfg_real.get_ast_node(as_tree, 3)

        self.assertEqual(node, as_tree.body[1].body[0])

    def test_get_ast_node_given_if_else(self):
        as_tree = ast.parse(ms("""\
                    a = 3
                    if a < 3:
                        z = 2
                    else:
                        y = 2
                    a = 4
                    """)
                            )

        cfg_real = Cfg()
        node = cfg_real.get_ast_node(as_tree, 5)

        self.assertEqual(node, as_tree.body[1].orelse[0])

    def test_get_ast_node_given_if_elif_else(self):
        as_tree = ast.parse(ms("""\
                    a = 3
                    if a < 3:
                        z = 2
                    elif z < 2:
                        x = 2
                    else:
                        y = 2
                    a = 4
                    """)
                            )

        cfg_real = Cfg()
        node = cfg_real.get_ast_node(as_tree, 5)

        self.assertEqual(node, as_tree.body[1].orelse[0].body[0])

    def test_get_ast_node_given_nested_if(self):
        as_tree = ast.parse(ms("""\
                    a = 3
                    if a < 3:
                        z = 2
                        if y < 2:
                            d = 2
                    a = 4
                    """)
                            )

        cfg_real = Cfg()
        node = cfg_real.get_ast_node(as_tree, 5)

        self.assertEqual(node, as_tree.body[1].body[1].body[0])

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
        for blocks in common.walk_block(cfg_real.block_list[0]):
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
        for blocks in common.walk_block(cfg_real.block_list[0]):
            blocks_list.append(blocks)
        pass

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
        cfg_real.root = common.delete_node(cfg_real.root, RawBasicBlock(1, 1))
        pass