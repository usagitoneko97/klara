import unittest
from textwrap import dedent

from klara.core import nodes
from klara.core.cfg import Cfg
from klara.core.tree_rewriter import AstBuilder
from klara.core.use_def_chain import DefUseLinker, link_stmts_to_def
from test.helper.base_test import BaseTestInference


class TestDefUseLinker:
    @staticmethod
    def setup_cfg(ast_str):
        as_tree = AstBuilder().string_build(ast_str)
        cfg = Cfg(as_tree)
        cfg.convert_to_ssa()
        return cfg

    def test_given_simple_link(self):
        cfg = self.setup_cfg(
            dedent(
                """\
                        x = 1
                        y = x
                        """
            )
        )
        DefUseLinker.link(cfg.block_list[-2].ssa_code.code_list[-1].value, cfg.block_list[0])
        assert cfg.block_list[-2].ssa_code.code_list[-1].value.links == cfg.block_list[-2].ssa_code.code_list[-2].value

    def test_given_attr(self):
        cfg = self.setup_cfg(
            dedent(
                """\
                        class Foo():
                            def __init__(self):
                                pass
                        x = Foo()
                        x.s = 5
                        y = x.s     # x and x.s is linked
                        """
            )
        )
        DefUseLinker.link(cfg.block_list[-2].ssa_code.code_list[-1].value, cfg.block_list[0])
        assert cfg.block_list[-2].ssa_code.code_list[-1].value.links == cfg.block_list[-2].ssa_code.code_list[-2].value


class TestUseDef(BaseTestInference):
    def test_use_def_simple_chain(self):
        _, cfg_real = self.build_tree_cfg(
            dedent(
                """\
                        x = 4
                        y = x / 1
                        z = 1 + y
                         """
            )
        )
        assert (
            cfg_real.block_list[1].ssa_code.code_list[1].value.left.links
            == cfg_real.block_list[1].ssa_code.code_list[0].value
        )
        assert (
            cfg_real.block_list[1].ssa_code.code_list[2].value.right.links
            == cfg_real.block_list[1].ssa_code.code_list[1].value
        )

    def test_use_def_phi_function(self):
        _, cfg_real = self.build_tree_cfg(
            dedent(
                """\
                        x = 4
                        if x < 2:
                            y = x
                        else:
                            y = 1.5
                        z = y
                         """
            )
        )
        assert (
            cfg_real.block_list[1].ssa_code.code_list[1].value.left.links
            == cfg_real.block_list[1].ssa_code.code_list[0].value
        )
        assert (
            cfg_real.block_list.get_block_by_name("L6").ssa_code.code_list[-1].value.links
            == cfg_real.block_list.get_block_by_name("L6").ssa_code.code_list[0].value
        )
        assert (
            cfg_real.block_list.get_block_by_name("L6").ssa_code.code_list[0].value.value[0].links
            == cfg_real.block_list.get_block_by_name("L3").ssa_code.code_list[0].value
        )
        assert (
            cfg_real.block_list.get_block_by_name("L6").ssa_code.code_list[0].value.value[1].links
            == cfg_real.block_list.get_block_by_name("L5").ssa_code.code_list[0].value
        )

    def test_use_def_with_attr(self):
        _, cfg_real = self.build_tree_cfg(
            dedent(
                """\
                        class Foo():
                            def __init__(self):
                                x = 1
                        z = Foo()
                        z.x = 1.3
                        y = z.x
                         """
            )
        )
        # asserting z.x
        assert (
            cfg_real.block_list.get_block_by_name("L5").ssa_code.code_list[-1].value.links
            == cfg_real.block_list.get_block_by_name("L5").ssa_code.code_list[-2].value
        )

    def test_use_def_return_val_from_other_scope(self):
        _, cfg_real = self.build_tree_cfg(
            dedent(
                """\
                        def foo():
                            return 4

                        y = foo()
                        x = y
                        """
            )
        )
        assert (
            cfg_real.block_list[-2].ssa_code.code_list[-1].value.links
            == cfg_real.block_list[-3].ssa_code.code_list[-1].value
        )

    def test_use_def_with_arg_and_ret_val(self):
        as_tree, cfg_real = self.build_tree_cfg(
            dedent(
                """\
                        def foo(x):
                            return x + 1

                        b = 2
                        y = foo(b)
                        x = y
                        """
            )
        )
        assert (
            cfg_real.block_list.get_block_by_name("L2").ssa_code.code_list[0].value.left.links
            == as_tree.body[0].args.args[0]
        )

    def test_use_def_given_class_with_self_init(self):
        _, cfg_real = self.build_tree_cfg(
            dedent(
                """\
                        class Foo():
                            def __init__(self, x):
                                self.x = x
                        foo = Foo(2)
                        y = foo.x
                        """
            )
        )
        # asserting foo.x
        assert (
            cfg_real.block_list[-2].ssa_code.code_list[0].value.links
            == cfg_real.block_list.get_block_by_name("L3").ssa_code.code_list[0].value
        )

    def test_use_def_given_expr_args_in_function(self):
        _, cfg_real = self.build_tree_cfg(
            dedent(
                """\
                        def foo(x):
                            return x + 1
                        y = 2
                        z = 4
                        foo(y + 2 / z * 43)
                        """
            )
        )
        assert (
            cfg_real.block_list[-2].ssa_code.code_list[-1].value.args[0].left.links
            == cfg_real.block_list.get_block_by_name("L3").ssa_code.code_list[0].value
        )

    def test_use_def_given_attr_in_function(self):
        _, cfg_real = self.build_tree_cfg(
            dedent(
                """\
                        class Temp:
                            def __init__(self):
                                x = 1

                        def foo(x):
                            return x + 1

                        y = Temp()
                        y.z = 3
                        foo(y.z)
                        """
            )
        )
        assert (
            cfg_real.block_list[-2].ssa_code.code_list[-1].value.args[0].links
            == cfg_real.block_list.get_block_by_name("L9").ssa_code.code_list[0].value
        )

    def test_use_def_with_nameconstant(self):
        _, cfg_real = self.build_tree_cfg(
            dedent(
                """\
                        x = 4
                        if True:
                            x = 3
                        elif x is None:
                            x = 4
                        else:
                            x = 5
                        y = x
                        """
            )
        )
        assert (
            cfg_real.block_list[-2].ssa_code.code_list[1].value.links
            == cfg_real.block_list[-2].ssa_code.code_list[0].value
        )

    def test_use_def_with_class_instance(self):
        _, cfg_real = self.build_tree_cfg(
            dedent(
                """\
                        class Phi:
                            def __init__(self, x):
                                self.x = 1

                        s = Phi()
                        y = s.x
                        """
            )
        )
        assert (
            cfg_real.block_list[-2].ssa_code.code_list[-1].value.links
            == cfg_real.block_list.get_block_by_name("L3").ssa_code.code_list[0].value
        )

    def test_use_def_given_class_with_self_init_call_twice(self):
        _, cfg_real = self.build_tree_cfg(
            dedent(
                """\
                        class Foo():
                            def __init__(self, x):
                                self.x = x
                        foo = Foo(2)
                        foo_1 = Foo(3)
                        y = foo.x + foo_1.x
                        """
            )
        )
        # asserting foo.x
        assert (
            cfg_real.block_list[-2].ssa_code.code_list[-1].value.left.links
            == cfg_real.block_list.get_block_by_name("L3").ssa_code.code_list[0].value
        )
        assert (
            cfg_real.block_list[-2].ssa_code.code_list[-1].value.right.links
            == cfg_real.block_list.get_block_by_name("L3").ssa_code.code_list[0].value
        )

    @unittest.skip("drop list assignment support")
    def test_use_def_list_assignment(self):
        _, cfg_real = self.build_tree_cfg(
            dedent(
                """\
                        l = [1, 2, 3]
                        l[1:] = [5, 6]
                        s = l[1:]
                        l[2] = 10
                        s = l[2]
                        """
            )
        )
        # asserting s = l[2]
        assert (
            cfg_real.block_list.get_block_by_name("L1").ssa_code.code_list[-1].value.links
            == cfg_real.block_list.get_block_by_name("L1").ssa_code.code_list[-2].value
        )
        # asserting s = l[1:]
        assert (
            cfg_real.block_list.get_block_by_name("L1").ssa_code.code_list[-3].value.links
            == cfg_real.block_list.get_block_by_name("L1").ssa_code.code_list[-4].value
        )

    def test_use_def_multiple_assignname(self):
        _, cfg_real = self.build_tree_cfg(
            dedent(
                """\
                        a = b = 1
                        c = b
                        d = a
                        """
            )
        )
        # asserting s = l[2]
        assert (
            cfg_real.block_list[1].ssa_code.code_list[1].value.links
            == cfg_real.block_list[1].ssa_code.code_list[0].value
        )
        assert (
            cfg_real.block_list[1].ssa_code.code_list[2].value.links
            == cfg_real.block_list[1].ssa_code.code_list[0].value
        )


class TestLinkStmtToDef:
    def test_link_1_var(self):
        # x = 2
        parent = nodes.LocalsDictNode()
        ast_source_node = nodes.Assign(parent=parent)
        ast_source_node.postinit(
            targets=[nodes.AssignName.quick_build(id="x", version=0, parent=ast_source_node)], value=nodes.Const(2)
        )
        parent.locals = {"x_0": ast_source_node}
        # y = x
        ast_target_node = nodes.Assign(parent=parent)
        ast_target_node.postinit(
            targets=[nodes.AssignName.quick_build(id="y", version=0, parent=ast_target_node)],
            value=nodes.Name.quick_build(id="x", version=0, parent=ast_target_node),
        )
        link_stmts_to_def(ast_target_node)
        assert ast_target_node.value.links == ast_source_node

    def test_var_replace(self):
        tree = AstBuilder().string_build(
            """\
            x = 3
            x = 2
            y = x
        """
        )
        tree.body[0].targets[0].version = 0
        tree.body[1].targets[0].version = 1
        tree.body[2].value.version = 1
        tree.locals["x_1"] = tree.body[1]
        link_stmts_to_def(tree.body[2])
        assert tree.body[2].value.links == tree.body[1]

    def test_var_not_exist(self):
        tree = AstBuilder().string_build(
            """\
            y = x
        """
        )
        tree.body[0].value.version = 0
        tree.body[0].targets[0].version = 0
        link_stmts_to_def(tree.body[0])
        assert tree.body[0].value.links is None
