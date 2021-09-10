from textwrap import dedent

from klara.core import cfg, manager, utilities
from klara.scripts.py_check import config, loop_solver

from ..helper.base_test import BaseTest

MANAGER = manager.AstManager()


def solve(ast_str, file_path="", float_config=None):
    args = float_config or config.ConfigNamespace()
    with utilities.temp_config(MANAGER, args):
        MANAGER.reload_protocol()
        as_tree = MANAGER.build_tree(ast_str)
        MANAGER.apply_transform(as_tree)
        cfg_ir = cfg.Cfg(as_tree)
        cfg_ir.apply_transform()
        cfg_ir.convert_to_ssa()
        return loop_solver.solve(cfg_ir, as_tree, ast_str, file_path, args)


class TestSolver(BaseTest):
    def test_for_while(self):
        result = solve(
            dedent(
                """\
            class CustomComp:
                def foo(self):
                    for i in range(3):
                        return i
                def fee(self):
                    def some():
                        while True:
                            pass
        """
            ),
            file_path="test.py",
        )
        assert (
            dedent(
                """\
        File: test.py
        In line: 3"""
            )
            in result
        )
        assert (
            dedent(
                """\
        File: test.py
        In line: 7"""
            )
            in result
        )

    def test_recursive_call_self(self):
        result = solve(
            dedent(
                """\
            class CustomComp:
                def foo(self):
                    self.foo()
        """
            ),
            file_path="test.py",
        )
        assert (
            dedent(
                """\
            File: test.py
            In line: 3"""
            )
            in result
        )

    def test_recursive_call_other(self):
        result = solve(
            dedent(
                """\
            class CustomComp:
                def fibonacci(self, n):
                    if n<0:
                        print("Incorrect input")
                    elif n==1:
                        return 0
                    elif n==2:
                        return 1
                    else:
                        return self.fibonacci(n-1)+self.fibonacci(n-2)
        """
            ),
            file_path="test.py",
        )
        assert (
            dedent(
                """\
                File: test.py
                In line: 10
                self.fibonacci((BinOp: n_0 - 1,))"""
            )
            in result
        )
        assert (
            dedent(
                """\
                File: test.py
                In line: 10
                self.fibonacci((BinOp: n_0 - 2,))"""
            )
            in result
        )

    def test_replaced(self):
        result = solve(
            dedent(
                """\
                class Comp:
                    def foo(self):
                        self.fee()
                    def fee(self):
                        self.foo = int
                        self.foo()
        """
            ),
            file_path="test.py",
        )
        assert not result

    def test_replaced_class_method(self):
        result = solve(
            dedent(
                """\
                class F:
                    def some(self):
                        self.others = int
                        self.others()
                    def others(self):
                        self.some()
        """
            ),
            file_path="test.py",
        )
        assert not result

    def test_alias(self):
        result = solve(
            dedent(
                """\
                class F:
                    def some(self):
                        something_else = self.others
                        something_else()
                    def others(self):
                        self.some()
        """
            ),
            file_path="test.py",
        )

        assert (
            dedent(
                """\
                File: test.py
                In line: 4
                something_else(())"""
            )
            in result
        )

    def test_phi(self):
        result = solve(
            dedent(
                """\
                class F:
                    def some(self):
                        something_else = self.others if self.number_b == 1 else self.some
                        something_else()
                    def others(self):
                        self.some()
        """
            ),
            file_path="test.py",
        )

        assert (
            dedent(
                """\
                    File: test.py
                    In line: 4
                    something_else(())"""
            )
            in result
        )
