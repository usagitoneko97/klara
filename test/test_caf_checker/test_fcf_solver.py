from textwrap import dedent

from klara.core import cfg, manager, utilities
from klara.scripts.py_check import config, fcf_solver
from klara.scripts.py_check.config import ConfigNamespace

from ..helper.base_test import BaseTest

MANAGER = manager.AstManager()

config_class = ConfigNamespace()


class AssertFloatWarning(object):
    def assert_float_warning_in_files(self, fcd_real, fcd_expected):
        for file, call_string_dict in fcd_real.items():
            assert file in fcd_expected, "{} is not in {}".format(file, fcd_expected)
            i = 0
            for call_stack, warning_in_trace in call_string_dict.items():
                assert len(warning_in_trace.warning) == len(fcd_expected[file][i])
                self.assert_warning_in_comp_id(warning_in_trace.warning, fcd_expected[file][i])
                i += 1

    def assert_warning_in_comp_id(self, real_lineno_dict, expected_lineno_dict):
        for sorted_lineno in sorted(real_lineno_dict):
            items_in_line = real_lineno_dict[sorted_lineno]
            assert sorted_lineno in real_lineno_dict, "lineno {} missing in real_lineno_dict".format(sorted_lineno)
            self.assert_float_warning_items_list(items_in_line, expected_lineno_dict[sorted_lineno])

    def assert_float_warning_in_file(self, list_real, list_expected):
        assert len(list_real) == len(list_expected), "number of expected comparison {} is not the same with {}".format(
            len(list_real), len(list_expected)
        )
        for real, expected in zip(list_real, list_expected):
            self.assert_float_warning_items_list(real, expected)

    def assert_float_warning_items_list(self, real_list, expected_list):
        assert len(real_list) == len(expected_list), "the number of list is not the same. {}, {}".format(
            len(real_list), len(expected_list)
        )
        for item_real, item_expected in zip(real_list, expected_list):
            self.assert_float_warning_item(item_real, item_expected)

    @staticmethod
    def assert_float_warning_item(real_item, expected_item):
        assert real_item.col_offset == expected_item.col_offset
        assert real_item.value == expected_item.value
        assert real_item.value_repr == expected_item.value_repr


def solve(ast_str, file_path="", float_config=None):
    args = float_config or config.ConfigNamespace()
    with utilities.temp_config(MANAGER, args):
        MANAGER.reload_protocol()
        as_tree = MANAGER.build_tree(ast_str)
        MANAGER.apply_transform(as_tree)
        cfg_ir = cfg.Cfg(as_tree)
        cfg_ir.apply_transform()
        cfg_ir.convert_to_ssa()
        return fcf_solver.solve(cfg_ir, as_tree, ast_str, file_path, args)


class TestSolver(AssertFloatWarning, BaseTest):
    def test_solver(self):
        result = solve(
            dedent(
                """\
                        z = 3
                        x = z * 4.5
                        x = x + 1
                        if z >= 6:     # will not flag
                            y = 60
                        elif x != 1:   # will flag
                            y = 2.5
                        else:
                            y = 3
                            if (x + 5) == 867:   # will flag
                                x = 987
                                k = y == 90   # will not flag
                        z = y == (z != 1.5)   # will flag twice
                            """
            )
        )
        assert (
            dedent(
                """\
                y = 2.5 (<class 'float'>)
                1.5 = 1.5 (<class 'float'>)"""
            )
            in result
        )
        assert (
            dedent(
                """\
                if (x + 5) == 867:   # will flag
                    ^
                x + 5 = 19.5 (<class 'float'>)
                """
            )
            in result
        )
        assert (
            dedent(
                """\
                elif x != 1:   # will flag
                     ^
                x = 14.5 (<class 'float'>)
                """
            )
            in result
        )

    def test_solver_with_attr(self):
        source_str = dedent(
            """\
                        class Foo():
                            def __init__(self):
                                y = 2
                                x = 1
                        z = Foo()
                        z.x = 1.3
                        z.y = 2
                        z.x == z.y
                            """
        )
        result = solve(source_str)
        assert (
            dedent(
                """\
                z.x == z.y
                ^
                z.x = 1.3 (<class 'float'>)
                """
            )
            in result
        )

    def test21(self):
        source_str = dedent(
            """\
                            def foo(x=2):
                                x == 1
                            foo(1.4)
                            foo(2.1)
                            """
        )
        result = solve(source_str)
        assert (
            dedent(
                """\
                x == 1
                ^
                x = 1.4 (<class 'float'>)
                """
            )
            in result
        )
        assert (
            dedent(
                """\
                x == 1
                ^
                x = 2.1 (<class 'float'>)
                """
            )
            in result
        )

    def test_type_inference_method(self):
        source_str = dedent(
            """\
                            Number = int
                            class Foo:
                                def foo(self, x: Number):
                                    y = x + 2 + 1 + 4
                                    y = y / 2
                                    1 == y
                            """
        )
        config = ConfigNamespace()
        config.analyze_procedure = True
        result = solve(source_str, file_path="test.py", float_config=config)
        assert (
            dedent(
                """\
                1 == y
                     ^
                y = Unknown value (<class 'float'>)"""
            )
            in result
        )

    def test_dunder_method_compare(self):
        source_str = dedent(
            """\
                            class Foo:
                                def __init__(self, x):
                                    self.x = x
                                def __ge__(self, other):
                                    1.6 == 1
                                    return 1.5
                            f = Foo()
                            (f >= 1.5) > 2
                            """
        )
        config = ConfigNamespace()
        result = solve(source_str, file_path="test.py", float_config=config)
        assert (
            dedent(
                """\
                In __ge__
                line: 5
                1.6 == 1
                ^
                1.6 = 1.6 (<class 'float'>)
                """
            )
            in result
        )
        assert (
            dedent(
                """\
                (f >= 1.5) > 2
                 ^
                f >= 1.5 = 1.5 (<class 'float'>)
                """
            )
            in result
        )

    def test_dunder_method_binop(self):
        source_str = dedent(
            """\
                            class Foo:
                                def __init__(self, x):
                                    self.x = x
                                def __add__(self, other):
                                    1.6 == other
                                    return 1.5
                            f = Foo()
                            (f + 1.5) > 2
                            """
        )
        config = ConfigNamespace()
        result = solve(source_str, file_path="test.py", float_config=config)
        assert (
            dedent(
                """\
                In __add__
                line: 5
                1.6 == other
                ^      ^
                1.6 = 1.6 (<class 'float'>)
                other = 1.5 (<class 'float'>)
                """
            )
            in result
        )
        assert (
            dedent(
                """\
                (f + 1.5) > 2
                 ^
                f + 1.5 = 1.5 (<class 'float'>)
                """
            )
            in result
        )

    def test_multi_line_if_expr(self):
        source_str = dedent(
            """\
                            x = 1.5
                            y = 1.6
                            z = (1 if cond else
                                 2 if y == 1 else
                                 3 if 4 == x else
                                3.5)
                            """
        )
        config = ConfigNamespace()
        result = solve(source_str, file_path="test.py", float_config=config)
        assert (
            (
                dedent(
                    """\
                line: 4
                2 if y == 1 else
                     ^
                y = 1.6 (<class 'float'>)
                """
                )
            )
            in result
        )

    def test_hidden_call(self):
        source_str = dedent(
            """\
                            class C(object):
                                def __init__(self):
                                    pass

                                def check(self, a=1.2, b=3.4):
                                    return a == b

                            if __name__ == '__main__':
                                assert(C().check() == False)
                                assert(C().check(4 / 2, 2))
                                assert(C().check(3 / 2, 1.5))
                            """
        )
        config = ConfigNamespace()
        config.py_version = 2
        result = solve(source_str, file_path="test.py", float_config=config)
        assert "Total number of floating-point warnings captured: 2" in result

    def test_called_func_analyze_procedure(self):
        source_str = dedent(
            """\
                            def foo(a):
                                a == 1.5
                            foo(1)
                            """
        )
        config = ConfigNamespace()
        config.analyze_procedure = True
        result = solve(source_str, file_path="test.py", float_config=config)
        assert "Total number of floating-point warnings captured: 1" in result

    def test_recursive_func(self):
        source_str = dedent(
            """\
                            def foo():
                                if some:
                                    foo()
                                1 == 1.5
                            foo()
                            """
        )
        config = ConfigNamespace()
        config.analyze_procedure = True
        result = solve(source_str, file_path="test.py", float_config=config)
        assert "Total number of floating-point warnings captured: 2" in result


class TestSolverWithConfig(BaseTest):
    def test_eq_neq(self):
        source_str = dedent(
            """\
                        class Foo:
                            def __init__(self, x):
                                self.x = x
                            def __ge__(self, other):
                                return 1.5
                        f = Foo()
                        (f >= 1) > 2 == 1.5 > 2.5
                        """
        )
        config = ConfigNamespace()
        config.eq_neq = True
        result = solve(source_str, file_path="test.py", float_config=config)
        assert (
            dedent(
                """\
                (f >= 1) > 2 == 1.5 > 2.5
                                ^
                1.5 = 1.5 (<class 'float'>)
                """
            )
            in result
        )

    def test_verbose(self):
        source_str = dedent(
            """\
                        class Foo:
                            def __init__(self, x):
                                self.x = x
                            def compare_float(self, y):
                                self.x == y
                        f = Foo(1.5)
                        x = 1.5
                        f.compare_float(x)
                        """
        )
        config = ConfigNamespace()
        config.verbose = 2
        result = solve(source_str, file_path="test.py", float_config=config).strip()
        assert (
            dedent(
                """\
                Traceback (most recent call last):
                File "test.py" line 4, in Foo
                Function compare_float in scope Class "Foo" in scope Module
                File "test.py"
                In Function compare_float in scope Class "Foo" in scope Module
                line: 5
                self.x == y
                ^         ^
                self.x = 1.5 (<class 'float'>)
                y = 1.5 (<class 'float'>)
                """
            )
            in result
        )
        config.verbose = 0
        result = solve(source_str, file_path="test.py", float_config=config).strip()
        assert (
            dedent(
                """\
                File "test.py"
                In compare_float
                line: 5
                self.x == y
                ^         ^
                self.x = 1.5 (<class 'float'>)
                y = 1.5 (<class 'float'>)
                """
            )
            in result
        )

    def test_hide_value(self):
        source_str = dedent(
            """\
                        x = 1 + 4
                        y = x == 1.5
                        """
        )
        config = ConfigNamespace()
        config.analyze_procedure = True
        result = solve(source_str, file_path="test.py", float_config=config)
        assert (
            dedent(
                """\
                y = x == 1.5
                         ^
                1.5 = 1.5 (<class 'float'>)
                """
            )
            in result
        )

    def test_analyze_procedure(self):
        source_str = dedent(
            """\
                        class Foo:
                            x = 1.6
                            x != 2
                            def __init__(self, x):
                                self.x = x
                            def compare_float(self, y: float):
                                1 == y
                        def foo():
                            1 == 1.6
                        """
        )
        config = ConfigNamespace()
        result = solve(source_str, file_path="test.py", float_config=config)
        assert (
            dedent(
                """\
                x != 2
                ^
                x = 1.6 (<class 'float'>)
                """
            )
            in result
        )
        assert (
            dedent(
                """\
                1 == y
                     ^
                y = Unknown value (<class 'float'>)
                """
            )
            in result
        )
        assert (
            dedent(
                """\
                1 == 1.6
                     ^
                1.6 = 1.6 (<class 'float'>)
                """
            )
            in result
        )

    def test_type_inference(self):
        source_str = dedent(
            """\
                        class Foo:
                            def __init__(self, x):
                                self.x = x
                            def compare_float(self, y: float, z: int):
                                f = y / z + y
                                f == 1
                        """
        )
        config = ConfigNamespace()
        config.analyze_procedure = True
        config.type_inference = False
        result = solve(source_str, file_path="test.py", float_config=config)
        assert result == ""

    def test_in_method(self):
        source_str = dedent(
            """\
                        class Foo:
                            def init(self, x):
                                self.ba = 1.5
                                self.ba == 1
                        """
        )
        config = ConfigNamespace()
        config.type_inference = False
        result = solve(source_str, file_path="test.py", float_config=config)
        assert (
            dedent(
                """\
                self.ba == 1
                ^
                self.ba = 1.5 (<class 'float'>)
                """
            )
            in result
        )


    def test_call_append(self):
        source_str = dedent(
            """\
                c = []
                c.append()
                        """
        )
        config = ConfigNamespace()
        config.py_version = 3
        result = solve(source_str, file_path="test.py", float_config=config)
        assert result == ""

    def test_for_in_range(self):
        source_str = dedent(
            """\
            class F:
                def f(self):
                    n = 3
                    for i in range(n):
                        if i < n:
                            pass

                    for i in range(n):
                        if i < n:
                            pass
        """
        )
        config = ConfigNamespace()
        config.py_version = 2
        result = solve(source_str, file_path="test.py", float_config=config)
        assert result == ""
