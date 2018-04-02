import unittest
import ast
from ssa import Ssa, SsaVariable, SsaCode
from common import *


class TestSsa(unittest.TestCase):
    def assert_ssa(self, ssa, target, left_oprd, right_oprd, operator=None):
        self.assertEqual(str(ssa.target), target)
        self.assertEqual(str(ssa.left_oprd), left_oprd)
        self.assertEqual(str(ssa.right_oprd), right_oprd)

        if operator is not None:
            self.assertEqual(ssa.operator, operator)

    def assert_ssa_list(self, ssa_list, target_list, left_oprd_list, right_oprd_list, operator_list=None):
        for i in range(len(ssa_list)):
            if operator_list is not None:
                self.assert_ssa(ssa_list[i], target_list[i], left_oprd_list[i], right_oprd_list[i], operator_list[i])
            else:
                self.assert_ssa(ssa_list[i], target_list[i], left_oprd_list[i], right_oprd_list[i], None)

    def test_SsaVariable_generation(self):
        ssa_var = SsaVariable('a')
        self.assertEqual(str(ssa_var), 'a_0')

        ssa_var = SsaVariable(3)
        self.assertEqual(str(ssa_var), '3')

    def test_ssa_generation_1_stmt(self):
        as_tree = ast.parse(ms("""\
            z = a + y"""))

        ssa_code = SsaCode(as_tree)
        expected_ssa_dict = {'z': 0, 'a': 0, 'y': 0}
        self.assertEqual(str(ssa_code), "z_0 = a_0 Add y_0\n")
        self.assertDictEqual(ssa_code.var_version_list, expected_ssa_dict)

    def test_ssa_generation_2_stmt(self):
        as_tree = ast.parse(ms("""\
            z = a + y
            x = b + c"""))

        ssa_code = SsaCode(as_tree)
        expected_ssa_dict = {'z': 0, 'a': 0, 'y': 0, 'x': 0, 'b': 0, 'c': 0}
        self.assertEqual(str(ssa_code), ms("""\
        z_0 = a_0 Add y_0
        x_0 = b_0 Add c_0
        """))
        self.assertDictEqual(ssa_code.var_version_list, expected_ssa_dict)

    def test_ssa_generation_2_stmt_expect_update_target(self):
        as_tree = ast.parse(ms("""\
            z = a + y
            z = a"""))

        ssa_code = SsaCode(as_tree)
        expected_ssa_dict = {'z': 1, 'a': 0, 'y': 0}
        self.assertEqual(str(ssa_code), "z_0 = a_0 Add y_0\nz_1 = a_0\n")
        self.assertDictEqual(ssa_code.var_version_list, expected_ssa_dict)

    def test_ssa_generation_2_stmt_expect_update_target_multiple_time(self):
        as_tree = ast.parse(ms("""\
            z = a + y
            z = a + y
            z = a
            a = y"""))

        ssa_code = SsaCode(as_tree)
        expected_ssa_dict = {'z': 2, 'a': 1, 'y': 0}
        self.assertEqual(str(ssa_code), ms("""\
        z_0 = a_0 Add y_0
        z_1 = a_0 Add y_0
        z_2 = a_0
        a_1 = y_0
        """))

        self.assertDictEqual(ssa_code.var_version_list, expected_ssa_dict)