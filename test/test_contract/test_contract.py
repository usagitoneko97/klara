"""
Generate pytest test case from z3 constraint result
"""

import pytest

import os
import pathlib
import sys
import tempfile
import unittest
from textwrap import dedent

from klara.contract.__main__ import run
from klara.contract.config import ContractConfig
from klara.klara_z3 import cov_manager, inference_extension

from ..helper import base_test

MANAGER = cov_manager.CovManager()


class KlaraBaseTest(base_test.BaseTest):
    _TEST_MODULE_NAME = "contract_test"
    unique_id = 0

    @classmethod
    def setUpClass(cls) -> None:
        config = ContractConfig()
        MANAGER.initialize(config)
        inference_extension.enable()

    def setUp(self) -> None:
        super(KlaraBaseTest, self).setUp()
        self.cwd = os.getcwd()

    def tearDown(self) -> None:
        super(KlaraBaseTest, self).tearDown()
        MANAGER.uninitialize()
        os.chdir(self.cwd)
        tst = "test_" + self._TEST_MODULE_NAME
        if tst in sys.modules:
            sys.modules.pop("test_" + self._TEST_MODULE_NAME)
        if self._TEST_MODULE_NAME in sys.modules:
            sys.modules.pop(self._TEST_MODULE_NAME)

    def assert_test_case_generation(self, test_input: str, expected_output: str):
        ret = run(test_input, self._TEST_MODULE_NAME)
        assert ret.strip() == expected_output.strip()
        # run pytest to make sure generated test passed
        self.assert_test_ran(test_input, ret)

    def assert_test_ran(self, test_input: str, test_case_generated: str):
        # run pytest to make sure generated test passed
        with tempfile.TemporaryDirectory() as tmpdirname:
            tmpdir = pathlib.Path(tmpdirname)
            input_file = tmpdir / (self._TEST_MODULE_NAME + ".py")
            input_file.write_text(test_input)
            output_test = tmpdir / ("test_" + self._TEST_MODULE_NAME + ".py")
            output_test.write_text(test_case_generated)
            os.chdir(str(tmpdir))
            ret_code = pytest.main(["test_" + self._TEST_MODULE_NAME + ".py"])
            assert ret_code == pytest.ExitCode.OK

    def assert_num_of_assert(self, test_case_generated: str, num_of_assert: int):
        assert sum("assert" in t for t in test_case_generated.split("\n")) == num_of_assert


class TestCaseGenerator(KlaraBaseTest):
    def test_triangle(self):
        test_case = dedent(
            """
            def triangle(x: int, y: int, z: int) -> str:
                if x == y == z:
                    return "Equilateral triangle"
                elif x == y or y == z or x == z:
                    return "Isosceles triangle"
                else:
                    return "Scalene triangle"
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 3)

    def test_string(self):
        test_case = dedent(
            """
            def foo(x: int, y: int, zz: str, z: str="value_default"):
                if x + y > 2:
                    return x + y + 12
                elif x < y:
                    return x + y
                elif (z + "me") == "some":
                    return z + "thing" + zz
                else:
                    return x - y
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 4)

    def test_undefined_result(self):
        test_case = dedent(
            """
            def foo(x: int, y: int):
                if x == 2 and y == 3:
                    return [1, 2, 3]
                else:
                    return {1, 2, 3}
        """
        )
        expected_output = dedent(
            """\
            import contract_test


            def test_foo_0():
                assert contract_test.foo(2, 3) is not None
                assert contract_test.foo(0, 0) is not None
        """
        )
        self.assert_test_case_generation(test_case, expected_output)

    def test_none_result(self):
        test_case = dedent(
            """
            def foo(x: int, y: int):
                if x != 2 or y != 100:
                    return None
                else:
                    return True
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)

    def test_default_arg(self):
        test_case = dedent(
            """
            def foo(x: int, y: int, default: str="") -> str:
                if x + y > 2:
                    return default + default
                else:
                    return x - y
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 2)

    @unittest.skip("String multiplication to be implemented")
    def test_string_mult(self):
        test_case = dedent(
            """
            def foo(x: int, y: int, default: str="") -> str:
                if x > 1 and (default * x) == "somethingsomething":
                    return default * (x + y)
                else:
                    return x - y
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 2)

    def test_func_call(self):
        test_case = dedent(
            """
            def fee(x, y):
                return x + y * y
                
            def foo(x: int, y: int) -> str:
                if fee(y, x) > 2:
                    return x + y
                else:
                    return x - y
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 2)

    def test_return_result_default(self):
        test_case = dedent(
            """
            def fee(x, y):
                return x + y * y
                
            def foo(x: int, y: int, z: str="default"):
                if fee(y, x) > 2:
                    return z
                else:
                    return x - y
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 2)

    def test_return_result_multiple_default_arg(self):
        test_case = dedent(
            """
            def fee(x, y):
                return x + y * y
                
            def foo(x: int, y: int, z: str="default", a: str=""):
                if fee(y, x) > 2:
                    return z + a
                elif a == "something":
                    return a
                else:
                    return x - y
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 3)


class TestContractRequireEnsure(KlaraBaseTest):
    def test_require_simple(self):
        test_case = dedent(
            """
            import icontract
            @icontract.require(lambda x, y: x + y > 100)
            def foo(x: int, y: int):
                if x > y:
                    return x + 5
                else:
                    return x - 10
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 2)

    def test_ensure_simple(self):
        test_case = dedent(
            """
            import icontract
            @icontract.ensure(lambda result: result > 100)
            def foo(x: int, y: int):
                if x > y:
                    return x + 5
                else:
                    return x - 10
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 2)

    def test_ensure_have_arg(self):
        test_case = dedent(
            """
            import icontract
            @icontract.ensure(lambda x, result: (result + x) > 100)
            def foo(x: int, y: int):
                if x > y:
                    return x + 5
                else:
                    return x - 10
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 2)

    def test_ensure_require(self):
        test_case = dedent(
            """
            import icontract
            @icontract.require(lambda y: y > 2555.5)
            @icontract.require(lambda x, y: x > 100 and y > 14.5)
            @icontract.ensure(lambda x, result: (result + x) > 1000)
            def foo(x: int, y: float):
                if x > y:
                    return x + 5
                else:
                    return x - 10
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 2)

    def test_invalid_preconditions(self):
        test_case = dedent(
            """
            import icontract
            @icontract.require(lambda x: x > 100)
            def foo(x: int):
                if x < 100:
                    return 1
                else:
                    return 2
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 1)

    def test_invalid_primitive_type(self):
        test_case = dedent(
            """
            import icontract
            @icontract.require(lambda x: x > 100)
            def foo(x: str):
                if x == "something":
                    return 1
                else:
                    return 2
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_num_of_assert(ret, 2)

    def test_not_supported_type(self):
        test_case = dedent(
            """
            import icontract
            
            class T:
                x: int = 0
                
            @icontract.require(lambda x: x is not None)
            def foo(x: T):
                if x.x == 2:
                    return 1
                else:
                    return 2
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        assert ret

    def test_bool_short_circuiting(self):
        test_case = dedent(
            """\
                def Top(x: int, y: str):
                    a = 11 if x > 2 else 13
                    b = 16 if y == "something" else 15
                    if a or b:
                        z = 1
                    else:
                        z = 2
                    return z
         """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 2)

    def test_ifexp_bool_context(self):
        test_case = dedent(
            """\
                def Top(x: int, y: str):
                    a = 11 if x else 13 if y else 111
                    b = 16 if y else 15 if x > 12 else 124
                    if (a and b and a or b):
                        z = 1
                    else:
                        z = 2
                    return z
         """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 5)

    def test_container_binop(self):
        test_case = dedent(
            """\
                def Top(x: int, y: str):
                    if 1 + x > 2:
                        return [1, 2] * x
                    else:
                        return "something" * x
         """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 2)

    def test_str_conversion(self):
        test_case = dedent(
            """\
                def Top(x: int, y: str):
                    if str(x) == "23" and y == "a number":
                        return "number is: " + str(x) + str(y)
                    else:
                        return "number is: " + str(x)
         """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 2)

    def test_complex_bin_op(self):
        test_case = dedent(
            """\
            import math
            class Cell: pass
            
            def Top(bn: int, en_pp: bool, re: bool, pp_num: int):
                # IO: have 55 io in each  local block
                max_rlc = 55
                nlc = (bn -1)/max_rlc + 1

                pp_num = pp_num + re
                if(en_pp):
                    nlc = 3
                    pp_num = pp_num + re

                bn = bn + nlc * re
                cell0 = Cell()
                cell1 = Cell()
                cell2 = Cell()
                cell3 = Cell()
                cell4 = Cell()
                cell5 = Cell()
                cell6 = Cell()
                pat1 = [cell0, cell1, cell2] if re else [cell2, cell3]
                pat2 = [cell1, cell2] if pp_num else [cell2, cell3]
                pat3 = [cell4, cell5] if re else [cell4, cell6]
                pattern1 = []
                if pp_num and bn == 1:
                    pattern1 = pat1 + pat2 * pp_num + pat3
                return pattern1
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 4)

    def test_list_mult(self):
        test_case = dedent(
            """\
            class Cell: pass
            
            def Top(bn: int, v: int):
                cell0 = Cell()
                cell1 = Cell()
                cell2 = Cell()
                cell3 = Cell()
                pat1 = [cell0, cell1, cell2] if bn > 2 else [cell2, cell3]
                z = 1 if v > 3 else 2
                return [0, 1, 2] + pat1 * z
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 4)

    def test_list_binop(self):
        test_case = dedent(
            """\
            class Cell: pass
            
            def Top(number: int, re: bool, en_pp: bool):
                cell = Cell()
                if en_pp:
                    cell1 = []
                elif re:
                    cell1 = [1] * re
                else:
                    cell1 = 0
                if number + re == 5 and re == 0:
                    ret = [0] + [cell1]
                else:
                    ret = [1]
                return ret
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 3)

    def test_explosive_result(self):
        test_case = dedent(
            """\
            import math
            
            def Top(number: int, pp_en: bool, re: bool, pp_key_num: int, x: int):
                # IO: have 55 io in each  local block
                max_rlc = 55
                nlc = (number -1)//max_rlc + 1

                pp_key_num = pp_key_num + re
                if(pp_en):
                    nlc = 3
                    pp_key_num = pp_key_num + re
                number = number + nlc * re
                number_2lc = 0

                if nlc == 2:
                    nio_1lc = int(math.ceil(float(number)/4))
                    number_1lc = nio_1lc * 2

                    number_2lc = number - number_1lc

                elif nlc == 3:
                    if pp_en:
                        number_1lc = pp_key_num
                    else:
                        nio_1lc = int(math.ceil(float(number)/6))
                        number_1lc = nio_1lc * 2

                    number_remain = number - number_1lc
                    nio_2lc = int(math.ceil(float(number_remain)/4))
                    number_2lc = nio_2lc * 2


                number_2lc = number_2lc - re
                if number_2lc <= 0:
                    x = "2"
                elif number_2lc <= 4:
                    x = "3"
                elif number_2lc <= 8:
                    x = "4"
                elif number_2lc <= 16:
                    x = "5"
                elif number_2lc <= 32:
                    x = "6"
                else:
                    x = "7"
                return x
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 10)

    def test_operand_model_changed(self):
        test_case = dedent(
            """\
            def Top(cm: int):
                pattern = 3
                if cm >= 2:
                    pattern = pattern * cm
                if cm <= 2:
                    pattern = pattern * cm
                return pattern
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 3)

    def test_bool_op(self):
        test_case = dedent(
            """\
            def Top(en: bool, bool1: bool):
                pattern = 3
                if not en and bool1:
                    pattern = pattern  + (not en and bool1)
                return pattern
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 2)

    def test_builtin_result(self):
        test_case = dedent(
            """\
            def Top(cm: int, en: bool):
                cell = None
                if cm > 2 and en:
                    cell = "cell_" + str(cm) * int(cm)
                return cell
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 2)

    def test_compare_multiple_comparators(self):
        test_case = dedent(
            """\
            def Top(pp_en: bool, cm: int, ss: int):
                if pp_en and cm == 2:
                    r = 2 + (cm or (pp_en and (cm <= 2) and (cm == 2)))
                elif (cm or ss) + 2 > 88:
                    r = 999
                else:
                    r = 2
                return r
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 3)

    def test_bool_node_error(self):
        test_case = dedent(
            """\
            def Top(pp_en: bool, cm: int, ss: int, s: str):
                if pp_en and cm == 2:
                    r = bool or pp_en
                elif (pp_en or s) > 0:
                    r = 999
                else:
                    r = 2
                return r
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_num_of_assert(ret, 3)

    def test_unrelated_arg(self):
        test_case = dedent(
            """\
            def Top(cm: int):
                if cm == 3:
                    e = 1
                else:
                    e = 2
                ret = 13
                if cm >= 50:
                    ret = 3
                return ret
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 2)

    def test_bool_and(self):
        test_case = dedent(
            """\
            def Top(pp_en: bool, cm: int, ss: int, s: str, en: bool):
                if not pp_en and cm == 2 and en:
                    r = (pp_en and en) or en
                elif (pp_en or s) > 0:
                    r = 999
                else:
                    r = 2
                return r
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_num_of_assert(ret, 3)

    def test_z3_bool_op(self):
        test_case = dedent(
            """\
            def Top(pp_en: bool, cm: int, ss: int, st: str):
                if ss == 0 and cm == 2:
                    r = (cm and ss) + 1     # 1
                elif cm == 0 and (cm or ss) == 13:
                    r = ss      # 13
                else:
                    r = st or ss
                return r
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_test_ran(test_case, ret)
        self.assert_num_of_assert(ret, 3)

    def test_identity_comparison(self):
        test_case = dedent(
            """\
            def Top(pp_en: bool, cm: int, mc: int):
                if cm == 2 and cm is mc and type(cm) is int:
                    return 3
                else:
                    return 4
        """
        )
        ret = run(test_case, self._TEST_MODULE_NAME)
        self.assert_num_of_assert(ret, 2)
