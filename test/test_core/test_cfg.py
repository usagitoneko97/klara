from textwrap import dedent

from klara.common import cfg_common
from klara.core.cfg import TEMP_ASSIGN, Cfg, GetBlocks, RawBasicBlock
from klara.core.tree_rewriter import AstBuilder
from test.helper.base_test import BaseTest
from test.helper.cfg_th import CfgTestAssertion


class TestCfg(BaseTest, CfgTestAssertion):
    @staticmethod
    def fill_nxt_block(cfg_expected, block_links):
        for i in range(len(block_links)):
            nxt_block_list = block_links.get(str(i))
            for nxt_block_num in nxt_block_list:
                cfg_expected.block_list[i].nxt_block.append(cfg_expected.block_list[nxt_block_num])

    # ------------------get_simple_block----------------------------
    def test_get_simple_block_given_no_indent(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
            a = 3
            a = 4
            """
            )
        )
        get_blocks_handler = GetBlocks(as_tree, as_tree.body)
        simple_block_list = []
        for simple_block in get_blocks_handler.get_basic_block():
            simple_block_list.append(simple_block)

        expected_block = RawBasicBlock(start_line=1, end_line=2)

        self.assertBasicBlockEqual(simple_block_list[0], expected_block)

    def test_get_simple_block_given_if(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
            a = 3
            if a < 3:
                b = 4
            c = 5
            """
            )
        )
        get_blocks_handler = GetBlocks(as_tree, as_tree.body)
        simple_block_list = []
        for basic_block in get_blocks_handler.get_basic_block():
            simple_block_list.append(basic_block)

        expected_block_0 = RawBasicBlock(start_line=1, end_line=2, block_end_type="If")
        expected_block_1 = RawBasicBlock(start_line=4, end_line=4)

        self.assertBasicBlockEqual(simple_block_list[0], expected_block_0, block_index=0)
        self.assertBasicBlockEqual(simple_block_list[1], expected_block_1, block_index=1)

    def test_get_simple_block_given_while(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
            a = 3
            while a < 3:
                b = 4
            c = 5
            """
            )
        )
        get_blocks_handler = GetBlocks(as_tree, as_tree.body)
        simple_block_list = []
        for basic_block in get_blocks_handler.get_basic_block():
            simple_block_list.append(basic_block)

        expected_block_0 = RawBasicBlock(start_line=1, end_line=2, block_end_type="While")
        expected_block_1 = RawBasicBlock(start_line=4, end_line=4)

        self.assertBasicBlockEqual(simple_block_list[0], expected_block_0)
        self.assertBasicBlockEqual(simple_block_list[1], expected_block_1)

    # ----------------- cfg test------------------

    def test_cfg_given_no_branch(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
            a = 3
            a = 4
            """
            )
        )
        cfg_real = Cfg(as_tree)

        self.assertCfgWithBasicBlocks(
            cfg_real,
            [None, None, "Module", "Module"],
            [1, 2, "", "L1"],
            [-1, -1, "", "PhiStub"],
            block_links={"0": [1], "1": [2], "2": []},
        )

    def test_cfg_given_if_else_without_link_tail(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
            a = 3           # 0
            if a > 3:       # 1
                a = 4       # 2
            else:           # 3
                z = 5       # 4
            """
            )
        )
        cfg_real = Cfg(as_tree)

        self.assertCfgWithBasicBlocks(
            cfg_real,
            [1, 2, "If", "L1"],
            [3, 3, "", "L3"],
            [5, 5, "", "L5"],
            [None, None, "Module", "Module"],
            [-1, -1, "", "PhiStub"],
            block_links={"0": [1, 2], "1": [4], "2": [4], "3": [0], "4": []},
        )

    def test_cfg_given_if_else_with_link_tail(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
            a = 3           # 1st
            if a > 3:       #  |
                a = 4       # 2nd
            else:           # 3rd
                z = 5       #  |
            y = 5           # 4th
            """
            )
        )
        cfg_real = Cfg(as_tree)

        self.assertCfgWithBasicBlocks(
            cfg_real,
            [1, 2, "If", "L1"],
            [3, 3, "", "L3"],
            [5, 5, "", "L5"],
            [6, 6, "", "L6"],
            [None, None, "Module", "Module"],
            [-1, -1, "", "PhiStub"],
            block_links={"0": [1, 2], "1": [3], "2": [3], "3": [5], "4": [0], "5": []},
        )

    def test_cfg_given_if_elif_no_else(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
            a = 3          #--- 1st
            if a > 3:      #---  |
                a = 4      #--- 2nd
            elif a < 1:    #--- 3rd
                a = 5      #--- 4th
            c = 5          #--- 5th
            """
            )
        )
        cfg_real = Cfg(as_tree)

        self.assertCfgWithBasicBlocks(
            cfg_real,
            [1, 2, "If", "L1"],
            [3, 3, "", "L3"],
            [4, 4, "If", "L4"],
            [5, 5, "", "L5"],
            [6, 6, "", "L6"],
            [None, None, "Module", "Module"],
            [-1, -1, "", "PhiStub"],
            block_links={"0": [1, 2], "1": [4], "2": [3, 4], "3": [4], "4": [6], "5": [0], "6": []},
        )

    def test_cfg_given_while(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
            while 3 < 4:
                x = 3
                if x < 2:
                    y = 5
            """
            )
        )
        cfg_real = Cfg(as_tree)

        self.assertCfgWithBasicBlocks(
            cfg_real,
            [1, 1, "While", "L1"],
            [2, 3, "If", "L2"],
            [4, 4, "", "L4"],
            [None, None, "Module", "Module"],
            [-1, -1, "", "PhiStub"],
            block_links={"0": [1, 4], "1": [2, 0], "2": [0], "3": [0], "4": []},
        )

    def test_cfg_given_simple_class(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                class SomeClass:
                    def __init__(self):
                        pass
            """
            )
        )
        cfg_real = Cfg(as_tree)
        self.assertCfgWithBasicBlocks(
            cfg_real,
            [1, 1, "ClassDef", "SomeClass"],
            [2, 2, "FunctionDef", "__init__"],
            [3, 3, "", "L3"],
            [None, None, "Module", "Module"],
            [1, 1, TEMP_ASSIGN, TEMP_ASSIGN],
            [2, 2, TEMP_ASSIGN, TEMP_ASSIGN],
            [-1, -1, "", "PhiStub"],
            [-1, -1, "", "PhiStub"],
            [-1, -1, "", "PhiStub"],
            block_links={"0": [5], "1": [2], "2": [6], "3": [4], "4": [7], "5": [6], "6": [], "7": [], "8": []},
        )

    def test_cfg_given_simple_class_stmt_between(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                class SomeClass:
                    if True:
                        x = 1
                    else:
                        x = 3
                    def __init__(self):
                        pass
            """
            )
        )
        cfg_real = Cfg(as_tree)
        self.assertCfgWithBasicBlocks(
            cfg_real,
            [1, 1, "ClassDef", "SomeClass"],
            [2, 2, "If", "L2"],
            [3, 3, "", "L3"],
            [5, 5, "", "L5"],
            [6, 6, TEMP_ASSIGN, TEMP_ASSIGN],
            block_links={"0": [1], "1": [2, 3], "2": [4], "3": [4], "4": []},
        )

    def test_cfg_given_while_body_if(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
            z = 2           # 0th block
            while a < 3:    # 1st block
                if a < 2:   # 2nd block
                     z = 2  # 3rd block
                b = 2       # 4th block
            c = 3           # 5th block
            """
            )
        )

        cfg_real = Cfg(as_tree)

        self.assertCfgWithBasicBlocks(
            cfg_real,
            [1, 1, "", "L1"],
            [2, 2, "While", "L2"],
            [3, 3, "If", "L3"],
            [4, 4, "", "L4"],
            [5, 5, "", "L5"],
            [6, 6, "", "L6"],
            block_links={"0": [1], "1": [2, 5], "2": [3, 4], "3": [4], "4": [1], "5": []},
        )

    def test_cfg_given_for(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
            for a in z:     # 0st block
                if a < 2:   # 1nd block
                     z = 2  # 2rd block
                b = 2       # 3th block
            z = 4
            """
            )
        )

        cfg_real = Cfg(as_tree)

        self.assertCfgWithBasicBlocks(
            cfg_real,
            [1, 1, "For", "L1"],
            [2, 2, "If", "L2"],
            [3, 3, "", "L3"],
            [4, 4, "", "L4"],
            [5, 5, "", "L5"],
            block_links={"0": [1, 4], "1": [2, 3], "2": [3], "3": [0], "4": []},
        )

    def test_cfg_given_for_with_else(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
            z = 2           # 0th block
            for a in z:     # 1st block
                if a < 2:   # 2nd block
                     z = 2  # 3rd block
                b = 2       # 4th block
            else:
                c = 3       # 5th block
            z = 4
            """
            )
        )

        cfg_real = Cfg(as_tree)

        self.assertCfgWithBasicBlocks(
            cfg_real,
            [1, 1, "", "L1"],
            [2, 2, "For", "L2"],
            [3, 3, "If", "L3"],
            [4, 4, "", "L4"],
            [5, 5, "", "L5"],
            [7, 7, "", "L7"],
            [8, 8, "", "L8"],
            block_links={"0": [1], "1": [2, 5, 6], "2": [3, 4], "3": [4], "4": [1], "5": [6], "6": []},
        )

    def test_delete_node(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
             z = 2           # 0th block
             while a < 3:    # 1st block
                 if a < 2:   # 2nd block
                      z = 2  # 3rd block
                 b = 2       # 4th block
             c = 3           # 5th block
             """
            )
        )

        cfg_real = Cfg(as_tree)
        cfg_real.root = cfg_common.delete_node(cfg_real.root, RawBasicBlock(1, 1))
        # TODO: test assert code

    def test_multi_line(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
             s = foo(1,
                     2,
                     3,
                     4)
             z = 1
             """
            )
        )
        cfg_real = Cfg(as_tree)
        self.assertCfgWithBasicBlocks(cfg_real, [1, 1, "Call", "L1"], [5, 5, "", "L5"], block_links={"0": [1]})


class TestCondition(BaseTest):
    def test_simple_cond(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                x = 2
                if x > 1:
                    stmt1
                else:
                    stmt2
             """
            )
        )
        cfg_real = Cfg(as_tree)
        l3 = cfg_real.block_list.get_block_by_name("L3")
        assert str(l3.get_conditions_from_prev()) == "{x > 1}"
        l5 = cfg_real.block_list.get_block_by_name("L5")
        results = {str(s) for s in l5.get_conditions_from_prev()}
        assert results == {"not(x > 1)"}
