import os
import pathlib
import sys
import unittest
from textwrap import dedent

from klara.core.cfg import Cfg
from klara.core.tree_rewriter import AstBuilder
from klara.klara_z3.cov_manager import CovManager
from klara.scripts.cover_gen_ins import config

from ..helper.base_test import BaseCovTest, BaseTestPatchCondResult

MANAGER = CovManager()


class TestFillCondition:
    def test_fill_if_else(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                x = 2
                if x > 1:
                    if y < 3:
                        stmt4
                elif x < -2:
                    stmt6
                stmt7
             """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.root.fill_conditions()
        results = {str(s) for s in cfg_real.block_list.get_block_by_name("L4").conditions}
        assert results == {"x > 1", "y < 3"}
        results = {str(s) for s in cfg_real.block_list.get_block_by_name("L6").conditions}
        assert results == {"not(x > 1)", "x < -(2)"}
        results = {str(s) for s in cfg_real.block_list.get_block_by_name("L7").conditions}
        assert results == set()

    def test_double_if(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                x = 2
                if x > 1:
                    pass
                if y < 3:
                    stmt4
             """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.root.fill_conditions()
        results = {str(s) for s in cfg_real.block_list.get_block_by_name("L4").conditions}
        assert results == set()


class TestSolveConditionsCompare(BaseTestPatchCondResult):
    def test_greater(self):
        self.solve_individual_block(
            dedent(
                """\
                def foo(x):
                    if x > 3:
                        pass
             """
            ),
            "L3",
        )
        self.assert_individual_block("L3", lambda args: args["x"] > 3)

    def test_greater_not(self):
        self.solve_individual_block(
            dedent(
                """\
                def foo(x):
                    if not(x >= 3):
                        pass
             """
            ),
            "L3",
        )
        self.assert_individual_block("L3", lambda args: args["x"] < 3)

    def test_not_equal(self):
        self.solve_individual_block(
            dedent(
                """\
                def foo(x):
                    if (x != 3 and x >= 3):
                        pass
             """
            ),
            "L3",
        )
        self.assert_individual_block("L3", lambda args: args["x"] != 3 and args["x"] >= 3)

    def test_not_equal_nested(self):
        self.solve_individual_block(
            dedent(
                """\
                def foo(x):
                    if (x != 3 and x <= 3):
                        pass
             """
            ),
            "L3",
        )
        self.assert_individual_block("L3", lambda args: args["x"] != 3 and args["x"] <= 3)

    def test_only_gt(self):
        self.solve_individual_block(
            dedent(
                """\
                def foo(x):
                    if -x >= -2 :
                        pass
                    if x >= 3:
                        if x <= 3:
                            pass

                foo(1)
             """
            ),
            "L6",
        )
        self.assert_individual_block("L6", lambda args: args["x"] == 3)

    @unittest.skip("Pending list getitem support in inference")
    def test_subscript(self):
        self.solve_individual_block(
            dedent(
                """\
                def foo(x):
                    z = [1, 2, 5.5, 7, 8]
                    (a, b, *c, d), e, f = z, 1, 3
                    res = c[0] + c[1] + e + f   # 16.5
                    if res + x <= 17.5:         # 16.5 + x <= 17.5
                        if x >= 1:
                            pass
                foo(-23)
             """
            ),
            "L7",
        )
        self.assert_individual_block("L7", lambda args: args["x"] == 1)


class TestSolveConditionsBinOp(BaseTestPatchCondResult):
    def test_nested_if(self):
        self.solve_individual_block(
            dedent(
                """\
                def foo(x):
                    z = x
                    f = z * 3 - 9
                    if f >= 3 - 6:
                        ss = f * 4
                        if ss >= 3:
                            pass
             """
            ),
            "L7",
        )
        self.assert_individual_block("L7", lambda args: args["x"] >= 39 / 12)

    def test_lte_and_gte(self):
        self.solve_individual_block(
            dedent(
                """\
                def foo(x):
                    if -x >= -3:
                        if -x <= -3:
                            pass
             """
            ),
            "L4",
        )
        self.assert_individual_block("L4", lambda args: args["x"] == 3)

    def test_equality_expr(self):
        self.solve_individual_block(
            dedent(
                """\
                def foo(x, y):
                    if x == 3:
                        if y == 4:
                            pass
             """
            ),
            "L4",
        )
        self.assert_individual_block("L4", lambda args: args["x"] == 3 and args["y"] == 4)

    def test_else_branch(self):
        self.solve_individual_block(
            dedent(
                """\
                def foo(x, y):
                    if x != 3:
                        pass
                    else:
                        if y != 2:
                            pass
                        else:
                            pass
             """
            ),
            "L8",
        )
        self.assert_individual_block("L8", lambda args: args["x"] == 3 and args["y"] == 2)

    def test_infeasible_solution(self):
        self.solve_individual_block(
            dedent(
                """\
                def foo(x):
                    if x >= 2:
                        if x <= 1:
                            pass    # impossible
             """
            ),
            "L4",
        )
        self.assert_individual_block("L4", None)

    def test_uninferable(self):
        self.solve_individual_block(
            dedent(
                """\
                if x == 1:
                    pass
             """
            ),
            "L2",
        )
        self.assert_individual_block("L2", None)

    def test_multiple_comparators(self):
        self.solve_individual_block(
            dedent(
                """\
                def foo(x, y, z):
                    if x <= y == 3 <= z:
                        pass
             """
            ),
            "L3",
        )
        self.assert_individual_block("L3", lambda args: args["x"] <= args["y"] == 3)

    def test_attribute(self):
        """By default, all node that didn't inferred to InferProxy will yield uninferable"""
        self.solve_individual_block(
            dedent(
                """\
                def foo(attr, x):
                    ins = attr
                    if x <= 3:
                        pass
             """
            ),
            "L4",
        )
        self.assert_individual_block("L4", lambda args: args["x"] <= 3)

    def test_class_method(self):
        """`self.value` is replaced by `y` because `self` will be ignored in substitution"""
        self.solve_individual_block(
            dedent(
                """\
                class F:
                    def foo(self, x, y):
                        if x <= 3:
                            if y == 4:
                                pass
             """
            ),
            "L5",
        )
        self.assert_individual_block("L5", lambda args: args["x"] <= 3 and args["y"] == 4)

    def test_invert_boolean(self):
        """test invert boolean operation"""
        self.solve_individual_block(
            dedent(
                """\
                def foo(x, y):
                    if not (x + 2 < 3):
                        pass
             """
            ),
            "L3",
        )
        self.assert_individual_block("L3", lambda args: not ((args["x"] + 2) < 3))

    def test_binop_boolop(self):
        """test boolean operation with binary operation"""
        self.solve_individual_block(
            dedent(
                """\
                def foo(x, y):
                    if not (x + y <= 2 and x <= 1):
                        pass
             """
            ),
            "L3",
        )
        self.assert_individual_block("L3", lambda args: not (args["x"] + args.get("y", -100) <= 2 and args["x"] <= 1))

    @unittest.skip("Pending list getitem support in inference")
    def test_container_assignment(self):
        """test boolean operation with binary operation"""
        self.solve_individual_block(
            dedent(
                """\
                def foo(x):
                    z = [1, 2, 5.5, 7, 8]
                    (a, b, *c, d), e, f = z, 1, 3
                    res = c[0] + c[1] + e + f   # 16.5
                    if res + x <= 17.5:         # 16.5 + x <= 17.5
                        if x >= 1:
                            pass
             """
            ),
            "L7",
        )
        self.assert_individual_block("L7", lambda args: round(args["x"], 3) == 1)

    def test_only_constants(self):
        """test only constant binary op"""
        self.solve_individual_block(
            dedent(
                """\
                def foo():
                    x = 5
                    y = 1 + 2 + 4
                    if y + 9 > x:
                        pass
             """
            ),
            "L5",
        )
        # FIXME: add test case


class TestSolveConditionsBoolOp(BaseTestPatchCondResult):
    def test_symbol(self):
        """[conditions solver] solve for symbol"""
        self.solve_individual_block(
            dedent(
                """\
                def foo(boolval):
                    if boolval:
                        pass
             """
            ),
            "L3",
        )
        self.assert_individual_block("L3", lambda args: args["boolval"] != 0)

    def test_int_test_like_bool(self):
        """[conditions solver] solve for int that tested like bool"""
        self.solve_individual_block(
            dedent(
                """\
                def foo(x):
                    if x:
                        pass
             """
            ),
            "L3",
        )
        self.assert_individual_block("L3", lambda args: args["x"] != 0)

    def test_symbol_or(self):
        """binary operation 'or' with symbol and const"""
        self.solve_individual_block(
            dedent(
                """\
                def foo(boolval):
                    if False or False or boolval:
                        pass
             """
            ),
            "L3",
        )
        self.assert_individual_block("L3", lambda args: args["boolval"] is True)

    def test_symbol_and(self):
        """boolean operation 'and' with symbol and const"""
        self.solve_individual_block(
            dedent(
                """\
                def foo(x, y):
                    if 1 and y and x:
                        pass
             """
            ),
            "L3",
        )
        self.assert_individual_block("L3", lambda args: args["x"] != 0 and args["y"] != 0)

    def test_boolean_operation(self):
        """boolean operation to use sympy.satisfiable()"""
        self.solve_individual_block(
            dedent(
                """\
                def foo(x, y):
                    if (x and not y):
                        pass
             """
            ),
            "L3",
        )
        self.assert_individual_block("L3", lambda args: args["x"] != 0 and args["y"] == 0)

    @unittest.skip("Bit vector to be implement")
    def test_bit_vector(self):
        self.solve_individual_block(
            dedent(
                """\
                def foo(x, y, z):
                    if (x & z > x) and (y << 2 > 4):
                        pass
             """
            ),
            "L3",
        )
        self.assert_individual_block("L3", lambda args: (args["x"] & args["z"] > 2) and (args["y"] << 2 > 4))

    @unittest.skip("Bit vector to be implement")
    def test_complex_bool(self):
        self.solve_individual_block(
            dedent(
                """\
                def foo(x, y, z):
                    if (x and not y) and (not(x&z) or y&x):
                        pass
             """
            ),
            "L3",
        )
        self.assert_individual_block("L3", lambda args: args["x"] != 0 and args["y"] == 0 and args.get("z", -9) == 0)

    def test_simple_or(self):
        self.solve_individual_block(
            dedent(
                """\
                def foo(x):
                    if x < 3 or x > 4:
                        pass
             """
            ),
            "L3",
        )
        self.assert_individual_block("L3", lambda args: (args["x"] < 3) or (args["x"] > 4))

    def test_repeating_or(self):
        self.solve_individual_block(
            dedent(
                """\
                def foo(x):
                    if x > 3 or x > 4:
                        pass
             """
            ),
            "L3",
        )
        self.assert_individual_block("L3", lambda args: (args["x"] > 3) or (args["x"] > 4))

    def test_or_no_result(self):
        """Test or with both elem has no solution"""
        self.solve_individual_block(
            dedent(
                """\
                def foo(x, y):
                    if (x < 3 and x > 4) or (y > 1 and y < 0):
                        pass
             """
            ),
            "L3",
        )
        self.assert_individual_block("L3", None)

    def test_and_or(self):
        """Test or nested in and"""
        self.solve_individual_block(
            dedent(
                """\
                def foo(x, y):
                    if (x < 3 or x > 4) and (y > 1 or y < 0):
                        pass
             """
            ),
            "L3",
        )
        self.assert_individual_block(
            "L3", lambda args: ((args["x"] < 3) or (args["x"] > 4) and args["y"] > 1 or args["y"] < 0)
        )

    def test_and_or_one_invalid(self):
        """Test or nested in and"""
        self.solve_individual_block(
            dedent(
                """\
                def foo(x, y):
                    if ((x < 3 and x > 4) or x > 4) and (y > 1 or y < 0):
                        pass
             """
            ),
            "L3",
        )
        self.assert_individual_block("L3", lambda args: args["y"] > 1 or args["y"] < 0)

    def test_other_bin_op_method(self):
        """test all bin op method"""
        self.solve_individual_block(
            dedent(
                """\
                def foo(x, y, z):
                    if (x*2 > (y / 3)) and (z // 2 == 6 or (z % 2 == 0)):
                        pass
             """
            ),
            "L3",
        )
        self.assert_individual_block(
            "L3", lambda args: (args["x"] * 2 > (args["y"] / 3) and (args["z"] // 2 == 6 or (args["z"] % 2 == 0)))
        )


class TestRegression(BaseTestPatchCondResult):
    """Test that failed"""

    def test_limitation_binary_and_boolean(self):
        """test boolean operation with binary operation."""
        self.solve_individual_block(
            dedent(
                """\
                def foo(a, b):
                    # this will generate error since `a` and `b` will be treated as boolean
                    # variable even though this is allowed in python.
                    if a and b and a < 3 and b == 3:
                        pass
             """
            ),
            "L5",
        )
        self.assert_individual_block(
            "L5", lambda args: args["a"] != 0 and args["b"] != 0 and args["a"] < 3 and args["b"] == 3
        )

    def test_complex_arithmetic(self):
        """test boolean operation with binary operation."""
        self.solve_individual_block(
            dedent(
                """\
                def foo(a, b):
                    if a < b:
                        if a + b > 100:
                            pass
             """
            ),
            "L4",
        )
        self.assert_individual_block("L4", lambda args: args["a"] - 3 < args["b"])


class TestCache(BaseTestPatchCondResult):
    """Similar condition to solve should cached"""

    def test_cache_simple(self):
        """test boolean operation with binary operation."""
        self.solve_individual_block(
            dedent(
                """\
                def foo(a, b):
                    if not (a == 3 and b == 4):
                        pass
                    if a != 3 and b != 4:
                        pass
             """
            ),
            "L3",
            "L5",
        )
        self.assert_individual_block("L5", lambda args: not (args.get("a") == 3 or args.get("b") == 4))


class BaseCoverageTest(BaseCovTest):
    @classmethod
    def setUpClass(cls):
        super(BaseCoverageTest, cls).setUpClass()
        sys.path.append(os.path.dirname(__file__))

    def setUp(self):
        super(BaseCoverageTest, self).setUp()
        MANAGER.transform.transform_cache.clear()
        MANAGER.initialize(config.ConfigNamespace())
        self.cwd = pathlib.Path(__file__).parent
        self.sample_data_xml = self.cwd / "sample_data.xml"

    def tearDown(self):
        super(BaseCoverageTest, self).tearDown()
        MANAGER.config = self._config_backup
        MANAGER.uninitialize()


class TestFunctional(BaseCoverageTest):
    def test_golden(self):
        test = dedent(
            """\
            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number = self.cfg["number"]
                    self.number_w = self.cfg["number_w"]
                    self.bool1 = self.cfg["bool1"]
                    self.var1 = self.cfg["var1"]

                    self.pr = self.number_w + self.cm
                    self.pc = self.number * self.cm

                def row(self, length=16):
                    if length >= 109:
                        c = 'q'
                    else:
                        c = 'b'
                    return self.var1 * [c] + ['s'] + [c, c, c, c, 's'] * int((length / 4))

                def rows(self, length=4):
                    return [self.row(self.pc)] * int(length)

                def Top(self):
                    rows = self.rows(self.pr)
                    cm = ('cm1' if self.cm == 1 else
                          'cm4' if self.cm == 4 else
                          'cm8' if self.cm == 8 else None)
                    ex = cm if self.number == 3 else rows
                    return ex
        """
        )
        self.run_solver_with_cov(test, 6, expected_return={"cm1", "cm4", "cm8", None})

    # FIXME: self.number_w + self.cm >= 23 conditions not added
    @unittest.skip("call context messed up after multiple calls since path evaluation comes after")
    def test_multi_function_call(self):
        test = dedent(
            """\
            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number = self.cfg["number"]
                    self.number_w = self.cfg["number_w"]
                    self.bool1 = self.cfg["bool1"]
                    self.var1 = self.cfg["var1"]

                    self.pr = self.number_w + self.cm
                    self.pc = self.number * self.cm

                def row(self, length=16):
                    if length >= 23:
                        c = 'q'
                    else:
                        c = 'b'
                    return self.var1 * [c] + ['s'] + [c, c, c, c, 's'] * int((length / 4))

                def rows(self, length=4):
                    return [self.row(length)] * int(length)

                def Top(self):
                    rows = self.rows(self.pr)
                    rows2 = self.rows(3)
                    cm = ('cm1' if self.cm == 1 else
                          'cm4' if self.cm == 4 else
                          'cm8' if self.cm == 8 else None)
                    ex = cm if self.number == 3 else rows + rows2
                    return ex
        """
        )
        self.run_solver_with_cov(test, 4)

    def test_sample_Class(self):
        test = dedent(
            """\
            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number = self.cfg["number"]
                    self.number_w = self.cfg["number_w"]
                    self.bool1 = self.cfg["bool1"]
                    self.var1 = self.cfg["var1"]

                    self.pr = self.number_w + self.cm
                    self.pc = self.number * self.cm

                def row(self, length=16):
                    c = 'q' if self.bool1 else 'b'
                    return self.var1 * [c] + ['s'] + [c, c, c, c, 's'] * int(length / 4)

                def rows(self, length=4):
                    return [self.row(self.pc)] * length

                def Top(self):
                    rows = self.rows(self.pr)
                    br = 3 if self.number_w > 4 else 5
                    other = True if self.bool1 else False
                    cm = ('cm1' if self.cm == 1 else
                          'cm4' if self.cm == 4 else
                          'cm8' if self.cm == 8 else None)
                    if br == 3:
                        ex = cm
                    elif other:
                        ex = br
                    else:
                        ex = 9
                    return ex
        """
        )
        self.run_solver_with_cov(test, 6, expected_return={"cm1", "cm4", "cm8", None, 5, 9})

    def test_function_return(self):
        test = dedent(
            """\
            class MyClass:
                def init(self):
                    self.number_w = self.cfg["number_w"]

                def rows(self):
                    cm = 4
                    if self.number_w > 4:
                        br = 4
                    else:
                        br = 5
                    if self.number_w == 65:
                        return cm
                    else:
                        return br

                def Top(self):
                    rows = self.rows()
                    return rows
        """
        )
        self.run_solver_with_cov(test, 3, expected_return={4, 5})

    def test_function_call(self):
        test = dedent(
            """\
            class MyClass:
                def init(self):
                    self.number_w = self.cfg["number_w"]
                    self.cm = self.cfg["cm"]
                    self.q = self.cfg["bool1"]

                def rows(self):
                    br = 4 if self.number_w > 4 else 5
                    other = True if self.q else False
                    cm = ('cm1' if self.cm == 1 else
                          'cm4' if self.cm == 4 else
                          'cm8' if self.cm == 8 else None)
                    if br == 4:
                        return cm
                    elif other:
                        return other
                    else:
                        return br

                def Top(self):
                    rows = self.rows()
                    if (self.cm < self.number_w):
                        ex = rows
                    else:
                        ex = 65
                    return ex
        """
        )
        self.run_solver_with_cov(test, 7, expected_return={"cm1", "cm4", "cm8", True, 5, 65})

    def test_other_cond(self):
        test = dedent(
            """\
            class MyClass:
                def init(self):
                    self.var1 = self.cfg["var1"]
                    self.var2 = self.cfg["var2"]

                def Top(self):
                    if self.var1 == 82:
                        ex = 4
                    elif (self.var1 + self.var2) >= 101:     # this condition will fail in ortools
                        ex = 5
                    else:
                        ex = 65
                    return ex
        """
        )
        self.run_solver_with_cov(test, 3, expected_return={4, 5, 65})

    def test_boolean(self):
        test = dedent(
            """\
            class MyClass:
                def init(self):
                    self.var1 = self.cfg["var1"]
                    self.var2 = self.cfg["var2"]
                    self.bool1 = self.cfg["bool1"]
                    self.bool2 = self.cfg["bool2"]

                def Top(self):
                    if self.bool1 and not self.bool2:
                        ex = 4
                    elif (self.var1 + self.var2) >= (100 - self.var2 * 2):
                        ex = 51
                    else:
                        ex = 65
                    return ex
        """
        )
        self.run_solver_with_cov(test, 3, expected_return={4, 51, 65})

    def test_string(self):
        test = dedent(
            """\
            
            class MyClass:
                def init(self):
                    self.red = self.cfg["bool1"]
                    self.other = self.cfg["bool2"]
                    self.strvar1 = self.cfg["strvar1"]
                    self.strvar2 = self.cfg["strvar2"]

                def Top(self):
                    if self.red and not self.other:
                        ex = 4
                    elif self.strvar1 + self.strvar2 == "SOMEPARAM":
                        ex = 123
                    else:
                        ex = 65
                    return ex
        """
        )
        self.run_solver_with_cov(test, 3, expected_return={4, 123, 65})

    def test_simple_minimal_instances(self):
        test = dedent(
            """\
            
            class MyClass:
                def init(self):
                    self.intvar1 = self.cfg["var1"]
                    self.intvar2 = self.cfg["var2"]
                    self.red = self.cfg["bool1"]
                    self.other = self.cfg["bool2"]
                    self.strvar1 = self.cfg["strvar1"]
                    self.strvar2 = self.cfg["strvar2"]

                def Top(self):
                    ex1, ex2, ex3, ex4, ex5 = 0, 0, 0, 0, 0
                    if self.red and not self.other:
                        ex1 = 4
                    if self.strvar1 + self.strvar2 == "SOMEPARAM":
                        ex2 = 123
                    if self.intvar1 > 23 and self.intvar2 > 24:
                        ex3 = 124
                    if self.intvar1 < 99 and self.intvar2 > 87:
                        ex4 = 12512
                    else:
                        ex5 = 65
                    return ex1 + ex2 + ex3 + ex4 + ex5
        """
        )
        self.run_solver_with_cov(test, 23)

    def test_nameconstant(self):
        test = dedent(
            """\
                
                class MyClass:
                    def init(self):
                        self.boolvar1 = self.cfg["bool1"]

                    def Top(self):
                        x = 1
                        if self.boolvar1 == True:
                            return x
                        else:
                            return x + 1
             """
        )
        self.run_solver_with_cov(test, 4, expected_return={1, 2})

    def test_multiple_values_cond(self):
        test = dedent(
            """\
            import math
            
            class MyClass:
                def init(self):
                    self.intvar = self.cfg["var1"]
                    self.number = self.cfg["number"]

                def Top(self):
                    x = 3 if self.intvar < 1 else 5
                    if x < self.number:
                        return x
                    else:
                        return x + 1
         """
        )
        self.run_solver_with_cov(test, 4, expected_return={3, 5, 4, 6})

    def test_nested_dependent_condition(self):
        test = dedent(
            """\
            
            class MyClass:
                def init(self):
                    self.intvar = self.cfg["var1"]
                    self.number = self.cfg["number"]

                def Top(self):
                    if self.intvar > 5:
                        x = 5
                    else:
                        x = 3
                    if x < self.number:
                        return x
                    else:
                        return x + 1
         """
        )
        self.run_solver_with_cov(test, 4, expected_return={3, 5, 4, 6})

    def test_phi_func_call_depend(self):
        test = dedent(
            """\
            import math
            
            class MyClass:
                def init(self):
                    self.intvar = self.cfg["var1"]
                    self.intvar2 = self.cfg["var2"]
                    self.number = self.cfg["number"]

                def other_func(self):
                    return 9

                def func(self):
                    if self.intvar2 > 12:
                        return 5
                    else:
                        return 6

                def Top(self):
                    if self.intvar > 11:
                        x = self.func
                    else:
                        x = self.other_func
                    if x() < self.number:
                        return 12
                    else:
                        return 13
         """
        )
        self.run_solver_with_cov(test, 6, expected_return={12, 13})

    def test_boolop_multi_values(self):
        test = dedent(
            """\
            import math
            
            class MyClass:
                def init(self):
                    self.intvar = self.cfg["var1"]
                    self.intvar2 = self.cfg["var2"]
                    self.number = self.cfg["number"]
                    if self.number == 4:
                        self.other = 3
                    else:
                        self.other = 5

                def Top(self):
                    if self.intvar > 11:
                        x = 10
                    else:
                        x = 11
                    if self.other == 5 and x == 11:
                        return 12
                    else:
                        return 13
         """
        )
        self.run_solver_with_cov(test, 4, expected_return={12, 13})

    def test_unaryop_wrapped_in_other(self):
        test = dedent(
            """\
            
            class MyClass:
                def init(self):
                    self.intvar = self.cfg["var1"]
                    self.intvar2 = self.cfg["var2"]
                    self.number = self.cfg["number"]
                    if self.number == 4:
                        self.other = 3
                    else:
                        self.other = 5

                def Top(self):
                    if self.intvar > 11:
                        x = 10
                    else:
                        x = 11
                    if self.other == 5  and x == 11:
                        return -x
                    else:
                        return 13
         """
        )
        self.run_solver_with_cov(test, 4, expected_return={13, -11})

    def test_boolop_uninferable(self):
        test = dedent(
            """\
            import math
            
            class MyClass:
                def init(self):
                    self.intvar = self.cfg["var1"]
                    self.intvar2 = self.cfg["var2"]
                    self.number = self.cfg["number"]
                    x = 5
                    if self.number == 4:
                        self.other = x and math.cos(1)
                    else:
                        self.other = 5

                def Top(self):
                    if self.intvar > 11:
                        x = 10
                    else:
                        x = 11
                    if self.other == 5  and x == 11:
                        return -x
                    else:
                        return 13
         """
        )
        self.run_solver_with_cov(test, 4, expected_return={-11, 13})

    def test_from_call_arg(self):
        test = dedent(
            """\
            
            class MyClass:
                def init(self):
                    self.intvar = self.cfg["var1"]
                    self.intvar2 = self.cfg["var2"]
                    self.number = self.cfg["number"]
                    x = 5
                    if self.number == 4:
                        self.other = x
                    else:
                        self.other = 5

                def Top(self):
                    if self.intvar > 11:
                        x = 11
                    else:
                        x = 2
                    if self.other == 5  and x == 11:
                        y = 10
                    else:
                        y = 20
                    top_lay = x + y
                    return top_lay
         """
        )
        self.run_solver_with_cov(test, 4)

    def test_chain_ifexpr(self):
        test = dedent(
            """\
            
            class MyClass:
                def init(self):
                    self.intvar = self.cfg["var1"]
                    self.intvar2 = self.cfg["var2"]
                    self.number = self.cfg["number"]
                    x = 5
                    if self.number == 4:
                        self.other = x
                    else:
                        self.other = 5

                def Top(self):
                    x = 3 if self.intvar < 1 else 5 if self.intvar > 4 else 6
                    if self.other == 5  and x == 6:
                        y = 5
                    else:
                        y = 13
                    top_lay = x + y
                    return top_lay
         """
        )
        self.run_solver_with_cov(test, 6)

    def test_call_arg(self):
        test = dedent(
            """\
            

            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number_b = self.cfg["number_w"]
                    if self.cm == 2:
                        self.cell1 = 1
                    else:
                        self.cell1 = 2
                    if self.number_b < 4:
                        self.cell2 = 3
                    else:
                        self.cell2 = 4

                def row(self):
                    if self.cm >= 4:
                        unique_cell = 7
                    else:
                        unique_cell = 8
                    other_cell = 9 if self.number_b < 2 else 10
                    return unique_cell + other_cell

                def Top(self):
                    another_row = self.cell1 + self.cell2
                    return another_row + self.row()
         """
        )
        self.run_solver_with_cov(test, 9)

    def test_typical_case(self):
        test = dedent(
            """\
            

            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number_b = self.cfg["number_b"]
                    self.cell1 = 3
                    self.cell2 = 5
                    if self.cm == 2:
                        self.cell1 = 6
                    if self.number_b > 4:
                        self.cell2 = 7
                    if self.cm + self.number_b >= 8:
                        self.cell1 = 8

                def row(self):
                    if self.cm >= 4:
                        unique_cell = 9
                    else:
                        unique_cell = 10
                    other_cell = 34 if self.number_b < 2 else 98
                    return unique_cell + other_cell

                def Top(self):
                    another_row = self.cell1 + self.cell2
                    if self.number_b > 6:
                        return [another_row + self.row()]
                    return self.cell1 + self.cell2 + self.row()
             """
        )
        self.run_solver_with_cov(test, 24)

    def test_complex_list_inference(self):
        test = dedent(
            """\
            

            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number_b = self.cfg["number_b"]
                    if self.cm == 2:
                        self.cell1 = 6
                    else:
                        self.cell1 = 3
                    if self.number_b > 4:
                        self.cell2 = 7
                    else:
                        self.cell2 = 5
                    if self.cm + self.number_b >= 8:
                        self.cell1 = 8

                def row(self):
                    if self.cm >= 4:
                        unique_cell = 9
                    else:
                        unique_cell = 10
                    other_cell = 34 if self.number_b < 2 else 98
                    return unique_cell + other_cell

                def Top(self):
                    colRow = 4
                    anRow = None
                    if (self.cm + self.number_b) == 5:
                        colRow = 3
                    else:
                        anRow = [self.cell1, self.cell2]
                    top = [self.row(), colRow, anRow]
                    return top
             """
        )
        self.run_solver_with_cov(test, 19)

    def test_call_arg_if_expr(self):
        test = dedent(
            """\
        

        class MyClass:
            def init(self):
                self.cm = self.cfg["cm"]
                self.number_b = self.cfg["number_b"]

            def Top(self):
                if self.cm == 2:
                    top_suppress_1 = [3]
                else:
                    top_suppress_1 = []
                if self.number_b == 3:
                    top_suppress_2 = [3]
                else:
                    top_suppress_2 = []
                top_suppress = top_suppress_1 + top_suppress_2
                another_suppress = [4] if self.cm >= 2 else [5]
                top = [3, top_suppress + another_suppress]
                return top
         """
        )
        self.run_solver_with_cov(test, 6)

    def test_ins_is_phi(self):
        test = dedent(
            """\
        

        class MyClass:
            def init(self):
                self.cm = self.cfg["cm"]
                self.number_b = self.cfg["number_b"]

            def Top(self):
                class C: x = 1
                if self.cm == 2:
                    t = C()
                else:
                    t = C()
                    t.x = 3
                return t.x
         """
        )
        self.run_solver_with_cov(test, 2)

    def test_multiple_same_bin_op_operand(self):
        test = dedent(
            """\
        
        class MyClass:
            def init(self):
                self.number_cd = self.cfg["number"]
                self.cm = self.cfg["cm"]
                self.number_b = self.cfg["number_b"]
                self.is_number_b1 = 1 if self.number_b == 1 else 0
                self.is_number_b4 = 1 if self.number_b == 4 else 0
                self.multi_bank = 1 if self.number_cd > 1 else 0

            def Top(self):
                cm = ('cm1' if self.cm == 1 else
                      'cm4' if self.cm == 4 else
                      'cm8' if self.cm == 8 else "cmNone")
                if cm == "cm4":
                    ex = cm
                else:
                    ex = "something"
                top = ex + "some" * self.is_number_b1 + ex + ex * self.is_number_b4 + "some" * self.multi_bank
                top_rename = 1 if self.is_number_b1 == 5 else 1
                return top * top_rename
        """
        )
        self.run_solver_with_cov(test, 24)

    def test_list_mult_0(self):
        test = dedent(
            """\
        
        class MyClass:
            def init(self):
                self.number_cd = self.cfg["number"]
                self.cm = self.cfg["cm"]
                self.number_b = self.cfg["number_b"]
                self.is_number_b1 = 1 if self.number_b == 1 else 0
                self.is_number_b4 = 1 if self.number_b == 4 else 0
                self.multi_bank = 1 if self.number_cd > 1 else 0

            def Top(self):
                if self.cm == 4:
                    ex = "cm4"
                else:
                    ex = "something"
                an = 1 if self.number_cd > 8 else 0
                ii = 5 if self.number_cd > 19 else 9
                top = [ex, ex] * self.is_number_b1 + [ex, an] * self.is_number_b4 # + [ii, an] * self.multi_bank
                return top
        """
        )
        self.run_solver_with_cov(test, 7)

    def test_list_mult_0_many_operands(self):
        test = dedent(
            """\
        
        class MyClass:
            def init(self):
                self.number_cd = self.cfg["number"]
                self.cm = self.cfg["cm"]
                self.number_b = self.cfg["number_b"]
                self.is_number_b1 = 1 if self.number_b == 1 else 0
                self.is_number_b4 = 1 if self.number_b == 4 else 0
                self.ss_ps = (self.number_b if self.cm >= 2 else self.number_b - 1 if self.cm >= 5 else self.number_b + 3 if self.cm >= 8 else self.number_b + 5)
                self.multi_bank = 1 if self.number_cd > 1 else 0
                self.numberrs1_req = 1
                self.numberrs2_req = (1 if self.ss_ps >= 2 else 0)
                self.numberrs3_req = (1 if self.ss_ps >= 3 else 0)
                self.numberrs4_req = (1 if self.ss_ps >= 4 else 0)
                self.numberrs5_req = (1 if self.ss_ps >= 5 else 0)
                self.numberrs6_req = (1 if self.ss_ps >= 6 else 0)
                self.numberrs7_req = (1 if self.ss_ps >= 7 else 0)
                self.numberrs8_req = (1 if self.ss_ps >= 8 else 0)

            def Top(self):
                top = ("[sss]" * self.numberrs5_req + \
                       "[xxx_seg2]" * self.numberrs2_req  + \
                       "[sss]"  * self.numberrs3_req  + \
                       "[xxx_seg3]" * self.numberrs3_req + \
                       "[sss]" * self.numberrs4_req + \
                       "[xxx_seg4]"  *  self.numberrs4_req + \
                       "[sss]"  *  self.numberrs5_req + \
                       "[xxx_seg5]"  *  self.numberrs5_req + \
                       "[sss]"  *  self.numberrs6_req + \
                       "[xxx_seg6]"  *  self.numberrs6_req + \
                       "[sss]"  *  self.numberrs7_req + \
                       "[xxx_seg7]"  *  self.numberrs7_req + \
                       "[sss]"  *  self.numberrs8_req + \
                       "[xxx_se]"  *  self.numberrs8_req +  \
                       "[end]")
                return top
        """
        )
        self.run_solver_with_cov(test, 19)

    def test_infer_product_in_evaluate_paths(self):
        test = dedent(
            """\
        
        class MyClass:
            def init(self):
                self.number_cd = self.cfg["number"]
                self.cm = self.cfg["cm"]
                self.number_b = self.cfg["number_b"]
                self.is_number_b1 = 1 if self.number_b == 1 else 0
                self.is_number_b4 = 1 if self.number_b == 4 else 0
                self.multi_bank = 1 if self.number_cd > 1 else 2 if self.number_cd < -2 else 3

            def Top(self):
                if self.multi_bank == 1:
                    ex = "cm4"
                elif self.multi_bank == 2:
                    ex = "something"
                else:
                    ex = "final"
                an = 1 if self.number_cd > 8 else 0
                ii = 5 if self.number_cd > 19 else 9
                top = [ex, ex] * self.is_number_b1 + [ex, an] * self.is_number_b4 # + [ii, an] * self.multi_bank
                return top
        """
        )
        self.run_solver_with_cov(test, 8)

    def test_builtins(self):
        test = dedent(
            """\
        
        class MyClass:
            def init(self):
                self.cm = self.cfg["cm"]

            def Top(self):
                if float(self.cm) / 2 == 3.0/2:
                    ex = "cm4"
                else:
                    ex = "cm5"
                top = [ex, ex] * 2
                return top
        """
        )
        self.run_solver_with_cov(test, 2)

    def test_builtin_str(self):
        test = dedent(
            """\
        
        class MyClass:
            def init(self):
                self.cm = self.cfg["cm"]

            def Top(self):
                if self.cm == 3:
                    ex = 3
                else:
                    ex = 4
                top = str(ex) + "something"
                return top
        """
        )
        self.run_solver_with_cov(test, 2)

    def test_float_div(self):
        test = dedent(
            """\
        
        class MyClass:
            def init(self):
                self.number = self.cfg["number"]
                self.ppen = self.cfg["ppen"]

            def Top(self):
                self.nlc = (self.number -1)/55 + 1
                if self.ppen:
                    self.nlc = 3
                    
                ex = "NULL"
                if self.nlc == 1:
                    ex = "cm4"
                elif self.nlc == 2:
                    ex = "cm5"
                elif self.nlc == 3:
                    ex = "cm6"
                return ex
        """
        )
        self.run_solver_with_cov(test, 5, expected_return={"cm4", "cm5", "cm6", "NULL"})

    def test_ifexp_const_cond(self):
        test = dedent(
            """\
            
            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number = self.cfg["number"]

                def Top(self, length=16):
                    c = 3 if True else 4 if True else 5
                    return c
        """
        )
        self.run_solver_with_cov(test, 6, expected_return={3})

    def test_list_mul_0_selected_operand_issue(self):
        test = dedent(
            """\
            
            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number = self.cfg["number"]

                def Top(self, length=16):
                    z = ["some"]
                    if self.cm == 2:
                        i = 0
                    else:
                        i = 1
                    return z * i
        """
        )
        self.run_solver_with_cov(test, 2, expected_return=[["some"], []])

    def test_mod_with_real(self):
        test = dedent(
            """\
            
            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number_w = self.cfg["number_w"]

                def Top(self, length=16):
                    z = self.cm * 0.5
                    y = self.number_w * 0.5
                    if z % y == 0:
                        return 2
                    else:
                        return 3
        """
        )
        self.run_solver_with_cov(test, 2, expected_return={2, 3})


class TestCallChain(BaseCoverageTest):
    def test_no_call_chain(self):
        test = dedent(
            """\
            
            class MyClass:
                def init(self):
                    self.cm = 10 if self.cfg["cm"] == 2 else 100 if self.cfg["cm"] == 5 else 1000
                    self.number = self.cfg["number"]
                
                def foo(self, number):
                    return number * self.cm

                def Top(self):
                    z = self.foo(3) + self.foo(4)
                    return z
        """
        )
        self.run_solver_with_cov(test, 3, expected_return={70, 700, 7000})

    def test_basic(self):
        test = dedent(
            """\
            
            class MyClass:
                def init(self):
                    self.cm = 10 if self.cfg["cm"] else 100
                    self.number = self.cfg["number"]
                
                def foo(self, number):
                    if number == 2:
                        a = 2
                    else:
                        a = 3
                    return a * self.cm

                def Top(self):
                    z = self.foo(self.number) + self.foo(self.number + 1)
                    return z
        """
        )
        self.run_solver_with_cov(test, 6, expected_return={50, 500, 60, 600})

    def test_nested_call_site(self):
        test = dedent(
            """\
            
            class MyClass:
                def init(self):
                    self.cm = 10 if self.cfg["cm"] else 100
                    self.number = self.cfg["number"]
                
                def fee(self, number_w):
                    if number_w == 3:
                        return 5
                    else:
                        return 6
                        
                def foo(self, number):
                    if number == 2:
                        a = 2
                    else:
                        a = 3
                    return a * self.cm + self.fee(number * 3)

                def Top(self):
                    z = self.foo(self.number) + self.foo(self.number + 1)
                    return z
        """
        )
        self.run_solver_with_cov(test, 8, expected_return={62, 512, 61, 71, 72, 511, 611, 612})

    def test_func_call_sel_operand(self):
        test = dedent(
            """\
        
        class MyClass:
            def init(self):
                self.number = self.cfg["number"]
                self.number_w = self.cfg["number_w"]
                self.cm = 0
                if self.number_w > 2:
                    if self.number > 2 and self.number > 2 or self.number > 2:
                        if self.number > 0:
                            if self.number_w > 2 or self.number_w > 2:
                                self.cm = 2
                else:
                    self.cm = 1
            
            def foo(self, cm):
                return cm * self.cm

            def Top(self):
                ret = 100 * self.cm + self.foo(100) + self.foo(200)
                return ret
        """
        )
        self.run_solver_with_cov(test, 3, expected_return={0, 400, 800})

    def test_bool_not_bound(self):
        test = dedent(
            """\
                
                class MyClass:
                    def init(self):
                        self.cm = self.cfg["cm"]
                        self.re = self.cfg["re"]
                        self.ppen = self.cfg["ppen"]

                    def Top(self):
                        if self.ppen:
                            cell = 1 * self.re
                        else:
                            cell = 2 * self.re
                        another = 10 * self.re if self.cm > 2 else 100 * self.re
                        return cell * another * self.ppen * self.re
        """
        )
        self.run_solver_with_cov(test, 8, expected_return={10, 100})
