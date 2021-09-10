import unittest
from collections import deque
from textwrap import dedent

from klara.core.cfg import Cfg
from klara.core.ssa_visitors import AstAttrSeparator, VariableGetter
from klara.core.tree_rewriter import AstBuilder


class TestEnumerate(unittest.TestCase):
    def test_ssa_generation_1_stmt(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
            a = 1
            y = 2
            z = a + y"""
            )
        )

        cfg = Cfg(as_tree)
        cfg.root.nxt_block_list[0].enumerate()
        expected_ssa_dict = {"z": deque([0]), "a": deque([0]), "y": deque([0])}
        real_ssa_dict = as_tree.ssa_record.var_version_list
        assert real_ssa_dict == expected_ssa_dict

    def test_ssa_generation_number(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
            z = 4"""
            )
        )

        cfg = Cfg(as_tree)
        cfg.root.nxt_block_list[0].enumerate()
        expected_ssa_dict = {"z": deque([0])}
        real_ssa_dict = as_tree.ssa_record.var_version_list
        assert real_ssa_dict == expected_ssa_dict

    def test_ssa_generation_2_stmt(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
            a = 1
            y = 2
            b = 3
            c = 4
            z = a + y
            x = b + c"""
            )
        )

        cfg = Cfg(as_tree)
        cfg.root.nxt_block_list[0].enumerate()
        expected_ssa_dict = {
            "z": deque([0]),
            "a": deque([0]),
            "y": deque([0]),
            "x": deque([0]),
            "b": deque([0]),
            "c": deque([0]),
        }
        real_ssa_dict = as_tree.ssa_record.var_version_list
        assert real_ssa_dict == expected_ssa_dict

    def test_ssa_generation_2_stmt_expect_update_target(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
            a = 0
            y = 1
            z = a + y
            z = a"""
            )
        )

        cfg = Cfg(as_tree)
        cfg.root.nxt_block_list[0].enumerate()
        expected_ssa_dict = {"z": deque([0, 1]), "a": deque([0]), "y": deque([0])}
        real_ssa_dict = as_tree.ssa_record.var_version_list
        assert real_ssa_dict == expected_ssa_dict


class TestVariableGetter:
    def test_1_target_1_value(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                        x = y + 1
                        """
            )
        )
        var_getter = VariableGetter.get_variable(as_tree)
        assert str(var_getter.targets) == "[x]"
        assert str(var_getter.values) == "[y]"

    def test_no_target_1_value(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                        y + 1
                        """
            )
        )
        var_getter = VariableGetter.get_variable(as_tree)
        assert str(var_getter.targets) == "[]"
        assert str(var_getter.values) == "[y]"

    def test_target_attributes(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                        x.y = y + 1
                        """
            )
        )
        var_getter = VariableGetter.get_variable(as_tree)
        assert str(var_getter.targets) == "[x.y]"
        assert str(var_getter.values) == "[x, y]"


class TestAstAttrSeparator:
    def test_2_attr_load(self):
        attr_node = AstBuilder().string_build("snake.colour").body[0].value
        ast_separator = AstAttrSeparator()
        ast_separator.visit(attr_node)
        load_set = {str(s) for s in ast_separator.load}
        assert load_set == {"snake.colour", "snake"}

    def test_2_attr_store_and_load(self):
        attr_node = AstBuilder().string_build("snake.colour = pig.egg").body[0]
        ast_separator = AstAttrSeparator()
        ast_separator.visit(attr_node.targets[0])
        load_set = {str(s) for s in ast_separator.load}
        store_set = {str(s) for s in ast_separator.store}
        assert load_set == {"snake"}
        assert store_set == {"snake.colour"}
        ast_separator.load.clear()
        ast_separator._base = ""
        ast_separator.visit(attr_node.value)
        load_set = {str(s) for s in ast_separator.load}
        assert load_set == {"pig", "pig.egg"}

    def test_3_attr(self):
        attr_node = AstBuilder().string_build("snake.colour.egg").body[0].value
        ast_sep = AstAttrSeparator()
        ast_sep.visit(attr_node)
        load_set = {str(s) for s in ast_sep.load}
        assert load_set == {"snake.colour.egg", "snake.colour", "snake"}
