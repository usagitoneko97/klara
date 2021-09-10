from textwrap import dedent

from klara.core.cfg import Cfg, GetBlocks, build_blocks
from klara.core.tree_rewriter import AstBuilder
from test.helper.base_test import BaseTest
from test.helper.cfg_th import CfgTestAssertion


class TestFuncTail(BaseTest):
    def test_func_tail_given_no_return(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                            def foo(x):
                                x = 2
                                x = x + 1
                            """
            )
        )

        cfg_real = Cfg(as_tree)
        get_block = cfg_real.block_list.get_block_by_name
        assert get_block("foo").func_tail == []

    def test_func_tail_given_return_once(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                            def foo(x):
                                if x < 2:
                                    x = 2
                                else:
                                    x = 3

                                return x
                            """
            )
        )

        cfg_real = Cfg(as_tree)
        get_block = cfg_real.block_list.get_block_by_name
        assert get_block("foo").func_tail == [get_block("L7")]

    def test_func_tail_given_nested_if_while(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                            def foo(x):
                                while x > 3:
                                    if x < 2:
                                        return 4
                                    else:
                                        return 3
                            """
            )
        )

        cfg_real = Cfg(as_tree)
        get_block = cfg_real.block_list.get_block_by_name
        assert get_block("foo").func_tail == [get_block("L4"), get_block("L6")]

    def test_func_tail_given_if_else(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                            def foo(x):
                                if x < 2:
                                    return x
                                else:
                                    return 3
                                return 5
                            """
            )
        )

        cfg_real = Cfg(as_tree)
        get_block = cfg_real.block_list.get_block_by_name
        assert get_block("foo").func_tail == [get_block("L3"), get_block("L5"), get_block("L6")]

    def test_func_tail_given_stmt_after_return(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                            def foo(x):
                                x = 2
                                return 5
                                x = 5
                            """
            )
        )

        cfg_real = Cfg(as_tree)
        get_block = cfg_real.block_list.get_block_by_name
        assert get_block("foo").func_tail == [get_block("L2")]

    def test_func_tail_given_only_if_with_no_else(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                            def foo(x):
                                if x < 2:
                                    return 5
                            """
            )
        )

        cfg_real = Cfg(as_tree)
        get_block = cfg_real.block_list.get_block_by_name
        assert get_block("foo").func_tail == [get_block("L3")]

    def test_func_tail_given_no_return_raise_if_else(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                            def foo(x):
                                if x < 2:
                                    z = 2
                                else:
                                    z = 3
                                    raise ValueError
                                raise TypeError
                            """
            )
        )
        cfg_real = Cfg(as_tree)
        get_block = cfg_real.block_list.get_block_by_name
        assert get_block("foo").func_tail == []


class TestGetBasicBlock(BaseTest, CfgTestAssertion):
    """
    test on function get_basic_block which does partitioning of code into blocks. This particular test class
    is only testing the partitioning of blocks with function def and function call
    """

    def test_get_basic_block_given_def(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                            y = 3

                            def foo(x):
                                y = x + 1
                                return y
                            """
            )
        )

        real_block_list = []
        get_blocks_handler = GetBlocks(as_tree, as_tree.body)
        for block in get_blocks_handler.get_basic_block():
            real_block_list.append(block)

        expected_block_list = build_blocks([1, 1, ""], [3, 3, "FunctionDef"], block_links=None)
        self.assertBasicBlockListEqual(real_block_list, expected_block_list, name_required=False)

    def test_get_basic_block_given_call(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                            def foo(x):
                                y = x + 1
                                return y

                            y = x
                            foo(3)
                            """
            )
        )

        real_block_list = []
        get_blocks_handler = GetBlocks(as_tree, as_tree.body)
        for block in get_blocks_handler.get_basic_block():
            real_block_list.append(block)

        expected_block_list = build_blocks([1, 1, "FunctionDef"], [5, 6, "Call"], block_links=None)
        self.assertBasicBlockListEqual(real_block_list, expected_block_list, name_required=False)
