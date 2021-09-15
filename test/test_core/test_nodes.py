import ast
from textwrap import dedent

import klara.core.nodes as nodes
from klara.core import exceptions, protocols
from klara.core.cfg import Cfg
from klara.core.tree_rewriter import AstBuilder, TreeRewriter

from ..helper.base_test import BaseTest


class TestNodes:
    def test_nodes(self):
        as_tree = ast.parse(
            """\
import foo
from foo import n, a
a: int = 1
i = (...)
z = i % 1
for z in s:
    i+=1
else:
    i-=2
assert i == 1
del i
yield i
yield from i
try:
    x = 1
except ValueError:
    pass
"""
        )
        tr = TreeRewriter()
        tr.visit_module(as_tree)
        pass

    def test_classdef(self):
        as_tree = ast.parse("class Foo: x = 1")
        tr = TreeRewriter()
        tr.visit_module(as_tree)
        pass


class TestParentInfo:
    def test_parent_of_node(self):
        as_tree = ast.parse("x = 1")
        tr = TreeRewriter()
        new_tree = tr.visit_module(as_tree)
        node = new_tree.body[0].value
        assert node.parent == new_tree.body[0]

    def test_scope_module(self):
        as_tree = ast.parse("x = 1")
        tr = TreeRewriter()
        new_tree = tr.visit_module(as_tree)
        stmt = new_tree.body[0]
        assert stmt.scope() == new_tree

    def test_scope_function_def(self):
        as_tree = ast.parse(
            dedent(
                """\
            def foo():
                x = 1
        """
            )
        )
        tr = TreeRewriter()
        new_tree = tr.visit_module(as_tree)
        stmt = new_tree.body[0].body[0]
        assert stmt.scope() == new_tree.body[0]

    def test_statement(self):
        as_tree = ast.parse(
            dedent(
                """\
            y = (x * 2) + 2
        """
            )
        )
        tr = TreeRewriter()
        new_tree = tr.visit_module(as_tree)
        node = new_tree.body[0].value.left.left
        assert node.statement() == new_tree.body[0]

    def test_async(self):
        as_tree = AstBuilder().string_build(
            """\
            async def f():
                async with something():
                    async for i in range(3):
                        await g()
            """
        )
        s = as_tree.body[0].body[0].body[0].body[0].value.scope()
        assert s == as_tree.body[0]


class TestBaseNode:
    def test_get_parent_of_type(self):
        tree = AstBuilder().string_build(
            """\
            def foo():
                y = 1
            class Cls():
                def fee():
                    x = 1
        """
        )
        assert tree.body[0].body[0].get_parent_of_type(nodes.FunctionDef) == tree.body[0]
        assert tree.body[1].body[0].body[0].get_parent_of_type(nodes.ClassDef) == tree.body[1]
        assert tree.body[1].body[0].body[0].get_parent_of_type(nodes.Module) == tree


class TestBaseContainer:
    def test_get_index(self):
        tree = AstBuilder().string_build(
            """\
            (a, b, c), d, e = z
            ((a, b, c), d, e), f, g = z
        """
        )
        # get the index of b
        assert tree.body[0].targets[0].get_index(tree.body[0].targets[0].elts[0].elts[1]) == (
            (0, 1),
            tree.body[0].targets[0].elts[0].elts[1],
        )

        # get the index of c
        assert tree.body[1].targets[0].get_index(tree.body[1].targets[0].elts[0].elts[0].elts[-1])[0] == (0, 0, 2)


class TestScopedNode:
    @staticmethod
    def assert_locals_str(expected_locals, real_locals):
        """assert the str repr of the locals value instead of the ast stmt"""
        for expected_key, expected_item in expected_locals.items():
            real_item = real_locals.get(expected_key)
            assert repr(real_item) == expected_item

    def test_function_type(self):
        tree = AstBuilder().string_build(
            """\
            def func():
                pass
            class C:
                def method(self):
                    pass

                @staticmethod
                def static():
                    pass

                @classmethod
                def cm(cls):
                    pass
        """
        )
        assert tree.body[0].type == "function"
        assert tree.body[1].body[0].type == "method"
        assert tree.body[1].body[1].type == "staticmethod"
        assert tree.body[1].body[2].type == "classmethod"

    def test_containing_scope(self):
        tree = AstBuilder().string_build(
            """\
            def foo():
                pass
            class Cls():
                def fee():
                    pass
        """
        )
        assert tree.containing_scope == [tree.body[0], tree.body[1]]
        assert tree.body[1].containing_scope == [tree.body[1].body[0]]

    def test_functiondef_return_nodes(self):
        tree = AstBuilder().string_build(
            """\
            def foo():
                if cond():
                    return 4
                else:
                    return 8
                return 5
        """
        )
        assert tree.body[0].return_nodes == [
            tree.body[0].body[0].body[0],
            tree.body[0].body[0].orelse[0],
            tree.body[0].body[-1],
        ]

    def test_locals_dict_if(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                    x = 1
                    y = 2
                    if x < 2:
                        pass
                        """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        assert as_tree.locals == {"x_0": as_tree.body[0].value, "y_0": as_tree.body[1].value}

    def test_locals_dict_multiple_assignment(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                        y = 3
                        x = 1
                        z = y
                        x = 1
                        """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        assert as_tree.locals == {
            "y_0": as_tree.body[0].value,
            "x_0": as_tree.body[1].value,
            "z_0": as_tree.body[2].value,
            "x_1": as_tree.body[3].value,
        }

    def test_locals_dict_functiondef(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                        def foo(x):
                            y = 2
                            return y
                        """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        self.assert_locals_str({"x_0": "Arg: 'x'", "y_0": "2", "ret_val_0": "y_0"}, as_tree.body[0].locals)

    def test_locals_nested_functiondef(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                        def foo(x):
                            def fee(y):
                                y = 2
                                return y
                        """
            ),
            name="test_mod",
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        self.assert_locals_str(
            {
                "x_0": "Arg: 'x'",
                "fee_0": "Proxy to the object: Function fee in scope Function foo in scope Module test_mod",
            },
            as_tree.body[0].locals,
        )

    def test_locals_functiondef_default_args(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
            def foo(x, y=1.5):
                f = 4
        """
            ),
            name="test_mod",
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        # y_0 = Arg: y because handling of default arg will be `infer_arg` job
        self.assert_locals_str({"x_0": "Arg: 'x'", "y_0": "Arg: 'y'", "f_0": "4"}, as_tree.body[0].locals)

    def test_locals_phi_function(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
            if True:
                x = 1
            else:
                x = 2
            y = x
        """
            ),
            name="test_mod",
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        self.assert_locals_str({"x_0": "1", "x_1": "2", "x_2": "Phi(x_0, x_1)", "y_0": "x_2"}, as_tree.locals)


class TestVariable:
    def test_repr_variable(self):
        tree = AstBuilder().string_build(
            """\
            a.b.c = s
        """
        )
        tree.body[0].targets[0].version = 2
        assert repr(tree.body[0].targets[0]) == "a.b.c_2"
        assert tree.body[0].targets[0].get_var_repr() == "c_2"

    def test_separate_members(self):
        tree = AstBuilder().string_build(
            """\
            a.b.c
            a
            z = a.b.c.d
        """
        )
        assert tree.body[0].value.separate_members() == ("a", "b", "c")
        assert tree.body[1].value.separate_members() == ("a",)
        assert tree.body[2].value.separate_members() == ("a", "b", "c", "d")

    def test_build_var(self):
        assert str(nodes.Variable.build_var(("a", "b", "c"))) == "a.b.c"
        assert str(nodes.Variable.build_var(("a",))) == "a"


class TestArguments:
    def test_argument_get_default(self):
        tree = AstBuilder().string_build(
            """\
            def foo(a, b, c=1, d=2.5, e=8, f="s", g="default"):
                pass
        """
        )
        assert tree.body[0].args.get_default("c").value == 1
        assert tree.body[0].args.get_default("f").value == "s"
        assert tree.body[0].args.get_default("a") is None
        assert tree.body[0].args.args[-1].get_default().value == "default"


class TestBootstrapBuiltinsAndDunder(BaseTest):
    def test_bootstrap(self):
        tree = AstBuilder().string_build(
            """\
            x = 1 + 3
        """
        )
        s = tree.body[0].value.left.locals["__add__"]
        assert str(s) == 'Function __add__ in scope Class "int" in scope Module'

    def test_get_dunder_compare(self):
        as_tree = AstBuilder().string_build(
            """\
            a = 1
            a > 2
            class F:
                def __gt__(self, other):
                    pass
            f = F()
            f > 1
        """
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        with self.assertRaises(exceptions.OperationIncompatible) as e:
            list(protocols.get_custom_dunder_method(as_tree.body[1].value.left, ">"))
        assert e.exception.msg == "the node: 1 is not of type ClassInstance"
        meth = list(protocols.get_custom_dunder_method(as_tree.body[-1].value.left, ">"))[0]
        assert str(meth) == 'Proxy to the object: Function __gt__ in scope Class "F" in scope Module'
        with self.assertRaises(exceptions.DunderUnimplemented) as e:
            list(protocols.get_custom_dunder_method(as_tree.body[-1].value.left, "<"))
        assert e.exception.method_name == "__lt__"

    def test_get_dunder_binop(self):
        as_tree = AstBuilder().string_build(
            """\
            a = 1
            a - 2
            class F:
                def __add__(self, other):
                    pass
            f = F()
        """
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        with self.assertRaises(exceptions.OperationIncompatible) as e:
            list(protocols.get_custom_dunder_method(as_tree.body[1].value.left, "-"))
        assert e.exception.msg == "the node: 1 is not of type ClassInstance"
        meth = list(protocols.get_custom_dunder_method(as_tree.body[-1].targets[0], "+"))[0]
        assert str(meth) == 'Proxy to the object: Function __add__ in scope Class "F" in scope Module'
        with self.assertRaises(exceptions.DunderUnimplemented) as e:
            list(protocols.get_custom_dunder_method(as_tree.body[-1].targets[0], "<"))
        assert e.exception.method_name == "__lt__"


class TestGlobalVar:
    def test_function_def_global(self):
        tree = AstBuilder().string_build(
            """\
            def foo():
                global x, y, z
                global f
        """
        )
        assert tree.body[0].global_var.keys() == {"x", "y", "z", "f"}


class TestAssignment(BaseTest):
    def check_list_and_tuple_unpack(self, target, value):
        tree = AstBuilder().string_build(
            """\
                {} = {}
                d
            """.format(
                target, value
            )
        )
        b_val = tree.body[0].get_rhs_value(tree.body[0].targets[0].elts[1])
        assert b_val == tree.body[0].value.elts[1]
        c_val = tree.body[0].get_rhs_value(tree.body[0].targets[0].elts[2])
        assert c_val == tree.body[0].value.elts[2]
        with self.assertRaises(ValueError):
            tree.body[0].get_rhs_value(tree.body[1].value)

    target_list = ["[a, b, c]", "a, b, c"]
    value_list = ["[1, 2, 3]", "1, 2, 3"]

    def test_list_and_tuple_unpack_to_list_tuple(self):
        for target, value in zip(self.target_list, self.value_list):
            yield self.check_list_and_tuple_unpack, target, value

    def test_unpack_variable_multiple_assignment(self):
        tree = AstBuilder().string_build(
            """\
                a, b, c, d = e, f, g, h = z
            """
        )
        s = tree.body[0].get_rhs_value(tree.body[0].targets[1].elts[-1])
        assert str(s) == "z[3]"

    def test_unpack_invalid(self):
        tree = AstBuilder().string_build(
            """\
                a, b, c, d = [1, 2, 3]
            """
        )
        with self.assertRaises(ValueError):
            tree.body[0].get_rhs_value(tree.body[0].targets[0].elts[-1])

    def test_unpack_variable(self):
        tree = AstBuilder().string_build(
            """\
                a, b, c, d = z
            """
        )
        s = tree.body[0].get_rhs_value(tree.body[0].targets[0].elts[-1])
        assert str(s) == "z[3]"

    def test_no_unpacking(self):
        tree = AstBuilder().string_build(
            """\
                a = 4, 5
            """
        )
        s = tree.body[0].get_rhs_value(tree.body[0].targets[0])
        assert s == tree.body[0].value

    def test_lhs_function_call(self):
        tree = AstBuilder().string_build(
            """\
                a, b = c, d = foo()
            """
        )
        s = tree.body[0].get_rhs_value(tree.body[0].targets[0].elts[0])
        assert repr(s) == "Call: foo(())[0]"

    def test_starred_last(self):
        tree = AstBuilder().string_build(
            """\
                a, *b = (1, 2, 3, 4)
                a, *b = a
            """
        )
        s = tree.body[0].get_rhs_value(tree.body[0].targets[0].elts[1])
        assert str(s) == "(2, 3, 4)"
        s = tree.body[1].get_rhs_value(tree.body[1].targets[0].elts[1])
        assert str(s) == "a[1::]"

    def test_starred_middle(self):
        tree = AstBuilder().string_build(
            """\
                a, *b, c = (1, 2, 3, 4, 5)
                a, *b, c = [1, 2, 3, 4, 5]
                a, *b, c, d = a
            """
        )
        s = tree.body[0].get_rhs_value(tree.body[0].targets[0].elts[1])
        assert str(s) == "(2, 3, 4)"
        s = tree.body[1].get_rhs_value(tree.body[1].targets[0].elts[1])
        assert str(s) == "[2, 3, 4]"
        s = tree.body[2].get_rhs_value(tree.body[2].targets[0].elts[1])
        assert str(s) == "a[1:-2:]"

    def test_starred_first(self):
        tree = AstBuilder().string_build(
            """\
                *a, b, c = (1, 2, 3, 4, 5)
                *a, b, c = [1, 2, 3, 4, 5]
                *a, b, c, d = a
            """
        )
        s = tree.body[0].get_rhs_value(tree.body[0].targets[0].elts[0])
        assert str(s) == "(1, 2, 3)"
        s = tree.body[1].get_rhs_value(tree.body[1].targets[0].elts[0])
        assert str(s) == "[1, 2, 3]"
        s = tree.body[2].get_rhs_value(tree.body[2].targets[0].elts[0])
        assert str(s) == "a[:-3:]"

    def test_nested_tuple(self):
        tree = AstBuilder().string_build(
            """\
                (a, b, *c, d), e, f = (1, 2, 3, 4, 5, 6), 7, 8
            """
        )
        s = tree.body[0].get_rhs_value(tree.body[0].targets[0].elts[0].elts[2])
        assert str(s) == "(3, 4, 5)"
        s = tree.body[0].get_rhs_value(tree.body[0].targets[0].elts[1])
        assert str(s) == "7"

    def test_nested_tuple_variable(self):
        tree = AstBuilder().string_build(
            """\
                (a, b, *c, d), e, f = z
                (a, b, *c, d), e, f = z, 1, 3
            """
        )
        s = tree.body[0].get_rhs_value(tree.body[0].targets[0].elts[0].elts[2])
        assert str(s) == "z[0][2:-1:]"
        s = tree.body[1].get_rhs_value(tree.body[1].targets[0].elts[0].elts[2])
        assert str(s) == "z[2:-1:]"

    # -----------------test get lhs value---------------------------
    def test_lhs_tuple_tuple(self):
        tree = AstBuilder().string_build(
            """\
                a, b = c, d
            """
        )
        s = tree.body[0].get_lhs_value(tree.body[0].value.elts[0])
        assert s == [tree.body[0].targets[0].elts[0]]

    def test_lhs_multiple_assignment(self):
        tree = AstBuilder().string_build(
            """\
                a, b = c, d = 3, 4
            """
        )
        s = tree.body[0].get_lhs_value(tree.body[0].value.elts[0])
        assert s == [tree.body[0].targets[0].elts[0], tree.body[0].targets[1].elts[0]]

    def test_lhs_expect_invalid_subscript(self):
        tree = AstBuilder().string_build(
            """\
                a = (1, 2, 3)
            """
        )
        s = tree.body[0].get_lhs_value(tree.body[0].value.elts[-1])
        assert s == [tree.body[0].targets[0]]
