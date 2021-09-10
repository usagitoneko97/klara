import os
import pathlib
import re
import sys
import unittest
from textwrap import dedent

from klara.core import nodes
from klara.klara_z3.cov_manager import CovManager
from klara.scripts.cover_gen_ins.config import ConfigNamespace

from ..helper.base_test import BaseCovTest, BaseTestInference

MANAGER = CovManager()


class Base(BaseCovTest):
    @classmethod
    def setUpClass(cls):
        super(Base, cls).setUpClass()
        sys.path.append(os.path.dirname(__file__))

    def setUp(self):
        super(Base, self).setUp()
        MANAGER.transform.transform_cache.clear()
        MANAGER.initialize(ConfigNamespace())
        self.cwd = pathlib.Path(__file__).parent
        self.sample_data_xml = self.cwd.parent / "test_cov_analysis" / "sample_data.xml"

    def tearDown(self):
        super(Base, self).tearDown()
        MANAGER.config = self._config_backup

    @staticmethod
    def get_lineno(ast_str: str):
        """get lineno annotated by #@"""
        lines = []
        for i, line in enumerate(ast_str.splitlines()):
            match = re.match(r".*#@", line.strip())
            if match:
                lines.append(i + 1)
        return lines

    def assert_result(self, results, func):
        assert func(results)


class TestCoverLines(Base):
    def test_simple(self):
        as_tree = dedent(
            """\

            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number_w = self.cfg["number_w"]
                    self.cell1 = xxx.Cell()
                    self.cell2 = xxx.Cell()
                    if self.number_w < 4:
                        if self.cm == 2:
                            pass
                        else:
                            self.cell1 = xxx.Cell() #@
        """
        )
        linenos = self.get_lineno(as_tree)
        self.run_and_assert_line_fix(as_tree, linenos, lambda args: args["number_w"] < 4 and args["cm"] != 2)

    def test_simple_minimal_instances(self):
        as_tree = dedent(
            """\

            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number_w = self.cfg["number_w"]
                    self.cell1 = xxx.Cell()
                    self.cell2 = xxx.Cell()
                    if self.number_w < 4:
                        if self.cm > 2:
                            pass
                        else:
                            self.cell1 = xxx.Cell() #@
                    if self.number_w < 2:
                        if self.cm > 3:
                            self.cell1 = xxx.Cell() #@
                        else:
                            self.cell1 = xxx.Cell() #@
        """
        )
        linenos = self.get_lineno(as_tree)
        self.run_and_assert_line_fix(as_tree, linenos, lambda args: args["number_w"] < 2, 2)

    def test_func_call(self):
        as_tree = dedent(
            """\

            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number_w = self.cfg["number_w"]
                    self.cell1 = xxx.Cell()
                    self.cell2 = xxx.Cell()
                    
                def func(self):
                    if self.number_w < 4:
                        if self.cm == 2:
                            pass
                        else:
                            self.cell1 = xxx.Cell() #@
        """
        )
        linenos = self.get_lineno(as_tree)
        self.run_and_assert_line_fix(as_tree, linenos, lambda args: args["number_w"] < 4 and args["cm"] != 2)

    def test_func_call_with_arg(self):
        as_tree = dedent(
            """\

            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number_w = self.cfg["number_w"]
                    self.cell1 = xxx.Cell()
                    self.cell2 = xxx.Cell()
                    self.func(self.cm, self.number_w)
                    
                def func(self, number_w, cm):
                    if number_w < 4:
                        if cm == 2:
                            pass
                        else:
                            self.cell1 = xxx.Cell() #@
        """
        )
        linenos = self.get_lineno(as_tree)
        self.run_and_assert_line_fix(as_tree, linenos, lambda args: args["cm"] < 4 and args["number_w"] != 2)

    def test_func_nested_call(self):
        as_tree = dedent(
            """\

            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number_w = self.cfg["number_w"]
                    self.cell1 = xxx.Cell()
                    self.cell2 = xxx.Cell()
                    self.func(self.number_w, self.cm)
                    
                def func(self, number_w, cm):
                    if number_w < 4:
                        if cm == 2:
                            pass
                        else:
                            self.cell1 = xxx.Cell() #@
                    self.nested_func(number_w, cm)
                
                def nested_func(self, number_w, cm):
                    if number_w + cm <= 8:
                        if cm - number_w >= 2:
                            another = xxx.Cell() #@
        """
        )
        linenos = self.get_lineno(as_tree)
        self.run_and_assert_line_fix(
            as_tree,
            linenos,
            lambda args: args["number_w"] < 4
            and args["cm"] != 2
            and (args["number_w"] + args["cm"] <= 8 and (args["cm"] - args["number_w"]) >= 2),
            1,
        )

    def test_two_call_site(self):
        as_tree = dedent(
            """\

            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number_w = self.cfg["number_w"]
                    self.cell1 = xxx.Cell()
                    self.cell2 = xxx.Cell()
                    self.func(self.number_w, self.cm)
                    self.caller()
                    
                def caller(self):
                    if self.cm == 2:
                        self.nested_func(self.cm + self.number_w, self.number_w * 3)
                    
                def func(self, number_w, cm):
                    if number_w < 4:
                        if cm == 2:
                            pass
                        else:
                            self.cell1 = xxx.Cell() #@
                    self.nested_func(number_w, cm)
                
                def nested_func(self, number_w, cm):
                    if number_w + cm <= 8:
                        if cm - number_w >= 2:
                            another = xxx.Cell() #@
        """
        )
        linenos = self.get_lineno(as_tree)
        self.run_and_assert_line_fix(
            as_tree,
            linenos,
            lambda args: args["number_w"] < 4
            and args["cm"] != 2
            and (args["number_w"] + args["cm"] <= 8 and (args["cm"] - args["number_w"]) >= 2),
            1,
        )

    def test_call_site_not_called_from_top(self):
        as_tree = dedent(
            """\

            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number_w = self.cfg["number_w"]
                    self.cell1 = xxx.Cell()
                    self.cell2 = xxx.Cell()
                    
                def caller(self):
                    self.nested_func(self.cm + self.number_w, self.cm)
                    
                def nested_func(self, number_w, cm):
                    if number_w + cm <= 8:
                        if cm - number_w >= 2:
                            another = xxx.Cell() #@
        """
        )
        linenos = self.get_lineno(as_tree)
        self.run_and_assert_line_fix(
            as_tree,
            linenos,
            lambda args: (
                args["cm"] + args["number_w"] + args["cm"] <= 8 and (args["cm"] - (args["cm"] + args["number_w"])) >= 2
            ),
            1,
        )

    def test_call_site_with_conditions(self):
        as_tree = dedent(
            """\

            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number_w = self.cfg["number_w"]
                    self.number_b = self.cfg["number_b"]
                    self.cell1 = xxx.Cell()
                    self.cell2 = xxx.Cell()
                    if self.number_b * 2 > 8:
                        self.caller(self.number_b)
                    
                def caller(self, a):
                    if a > 5:
                        self.nested_func(self.cm + self.number_w, self.cm)
                    
                def nested_func(self, number_w, cm):
                    if number_w + cm <= 8:
                        if cm - number_w >= 2:
                            another = xxx.Cell() #@
        """
        )
        linenos = self.get_lineno(as_tree)
        self.run_and_assert_line_fix(
            as_tree,
            linenos,
            lambda args: (
                args["cm"] + args["number_w"] + args["cm"] <= 8
                and (args["number_b"] * 2 > 8 and args["number_b"] > 5)
                and (args["cm"] - (args["cm"] + args["number_w"])) >= 2
            ),
            1,
        )

    def test_only_bound_in_call(self):
        as_tree = dedent(
            """\

            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number_w = self.cfg["number_w"]
                    self.number_b = self.cfg["number_b"]
                    self.cell1 = xxx.Cell()
                    self.cell2 = xxx.Cell()
                    if self.number_b * 2 > 8:
                        self.caller(self.number_b)
                    
                def caller(self, a):
                    self.nested_func()
                    
                def nested_func(self):
                    another = xxx.Cell() #@
        """
        )
        linenos = self.get_lineno(as_tree)
        self.run_and_assert_line_fix(as_tree, linenos, lambda a: a["number_b"] * 2 > 8, 1)

    def test_stmt_no_conditions(self):
        as_tree = dedent(
            """\

            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number_w = self.cfg["number_w"]
                    self.number_b = self.cfg["number_b"]
                    self.cell1 = xxx.Cell()
                    self.cell2 = xxx.Cell()     #@
                    
                def Top(self, number_w, cm):
                    self.cell2 = xxx.Cell()     #@
        """
        )
        linenos = self.get_lineno(as_tree)
        self.run_and_assert_line_fix(as_tree, linenos, lambda args: True, 0)

    def test_all_mss_algorithm(self):
        as_tree = dedent(
            """\

            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number_w = self.cfg["number_w"]
                    self.number_b = self.cfg["number_b"]
                    self.cell1 = xxx.Cell()
                    self.cell2 = xxx.Cell()
                    if self.number_b * 2 > 8:
                        self.caller(self.number_b)
                    
                def caller(self, a):
                    self.nested_func()
                    
                def nested_func(self):
                    another = xxx.Cell() #@
        """
        )
        linenos = self.get_lineno(as_tree)
        self.run_and_assert_line_fix(as_tree, linenos, lambda a: a["number_b"] * 2 > 8, 1, mss_algorithm="z3")
        self.run_and_assert_line_fix(as_tree, linenos, lambda a: True, 0, mss_algorithm="legacy")


class TestCoverAll(Base):
    def test_simple(self):
        as_tree = dedent(
            """\

            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number_w = self.cfg["number_w"]
                    self.number_b = self.cfg["number_b"]
                    self.cell1 = xxx.Cell()
                    self.cell2 = xxx.Cell()
                    if self.number_b * 2 > 8:
                        self.caller(self.number_b)
                    
                def caller(self, a):
                    if a > 5:
                        self.nested_func(self.cm + self.number_w, self.cm)
                    
                def nested_func(self, number_w, cm):
                    if number_w + cm <= 8:
                        if cm - number_w >= 2:
                            another = xxx.Cell() #@
        """
        )
        self.run_fix_all_and_assert_line_fix(
            as_tree,
            lambda args: (
                args["cm"] + args["number_w"] + args["cm"] <= 8
                and (args["number_b"] * 2 > 8 and args["number_b"] > 5)
                and (args["cm"] - (args["cm"] + args["number_w"])) >= 2
            ),
        )

    @unittest.skip("pending test implementation")
    def test_cache(self):
        as_tree = dedent(
            """\

            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number_w = self.cfg["number_w"]
                    self.number_b = self.cfg["number_b"]
                    self.cell1 = xxx.Cell()
                    self.cell2 = xxx.Cell()
                    if self.number_b * 2 > 8:
                        s = 1
                        if self.cm * 2 == 4:
                            s = 2
                            s = 3
                    elif self.cm * 4 > 4:
                        s = 3
        """
        )
        self.run_fix_all_and_assert_line_fix(
            as_tree,
            lambda args: (
                args["cm"] + args["number_w"] + args["cm"] <= 8
                and (args["number_b"] * 2 > 8 and args["number_b"] > 5)
                and (args["cm"] - (args["cm"] + args["number_w"])) >= 2
            ),
        )


class TestStmtsVisitor(BaseTestInference):
    def test_stmt(self):
        as_tree, _ = self.build_tree_cfg(
            dedent(
                """

            class MyClass:
                x = 1
                def init(self):
                    def foo():
                        self.cm = self.cfg["cm"]
                    self.cm = self.cfg["cm"]
                    self.number_w = self.cfg["number_w"]
                    self.cell1 = xxx.Cell()
                    self.cell2 = xxx.Cell()
                    self.func(self.number_w, self.cm)
                    self.caller()
                    
                def caller(self):
                    self.nested_func(self.cm + self.number_w, self.number_w * 3)
                    
                def func(self, number_w, cm):
                    if number_w < 4:
                        if cm == 2:
                            pass
                        else:
                            self.cell1 = xxx.Cell()
                            self.cell1 = xxx.Cell()
                    self.nested_func(number_w, cm)
                
                def nested_func(self, number_w, cm):
                    if number_w + cm <= 8:
                        if cm - number_w >= 2:
                            another = xxx.Cell() if self.cm else xxx.Another()
                    while True:
                            another = xxx.Cell()
        """
            )
        )
        stmts = list(as_tree.get_statements())
        assert len(stmts) == 15
        for s in stmts:
            assert isinstance(s, nodes.Statement)
