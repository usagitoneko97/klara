import unittest
import ast
from ssa import Ssa, SsaVariable, SsaCode
from cfg_common import *


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

    def assertVariableVersionStack(self, real_dict, expected_dict):
        self.assertEqual(len(real_dict), len(expected_dict))
        for var, stack in real_dict.items():
            self.assertListEqual(stack.items, expected_dict[var])

    def test_SsaVariable_generation(self):
        ssa_var = SsaVariable('a')
        self.assertEqual(str(ssa_var), 'a_0')

        ssa_var = SsaVariable(3)
        self.assertEqual(str(ssa_var), '3')

    def test_ssa_generation_1_stmt(self):
        as_tree = ast.parse(ms("""\
            z = a + y"""))

        ssa_code = SsaCode(as_tree)
        expected_ssa_dict = {'z': [0], 'a': [0], 'y': [0]}
        self.assertEqual(str(ssa_code), "z_0 = a_0 Add y_0\n")
        self.assertVariableVersionStack(ssa_code.var_version_list, expected_ssa_dict)

    def test_ssa_generation_number(self):
        as_tree = ast.parse(ms("""\
            z = 4"""))

        ssa_code = SsaCode(as_tree)
        expected_ssa_dict = {'z': [0], 4: [0]}
        self.assertEqual(str(ssa_code), "z_0 = 4\n")
        self.assertVariableVersionStack(ssa_code.var_version_list, expected_ssa_dict)

    def test_ssa_generation_2_stmt(self):
        as_tree = ast.parse(ms("""\
            z = a + y
            x = b + c"""))

        ssa_code = SsaCode(as_tree)
        expected_ssa_dict = {'z': [0], 'a': [0], 'y': [0], 'x': [0], 'b': [0], 'c': [0]}
        self.assertEqual(str(ssa_code), ms("""\
        z_0 = a_0 Add y_0
        x_0 = b_0 Add c_0
        """))
        self.assertVariableVersionStack(ssa_code.var_version_list, expected_ssa_dict)

    def test_ssa_generation_2_stmt_expect_update_target(self):
        as_tree = ast.parse(ms("""\
            z = a + y
            z = a"""))

        ssa_code = SsaCode(as_tree)
        expected_ssa_dict = {'z': [0, 1], 'a': [0], 'y': [0]}
        self.assertEqual(str(ssa_code), "z_0 = a_0 Add y_0\nz_1 = a_0\n")
        self.assertVariableVersionStack(ssa_code.var_version_list, expected_ssa_dict)

    def test_ssa_generation_2_stmt_expect_update_target_multiple_time(self):
        as_tree = ast.parse(ms("""\
            z = a + y
            z = a + y
            z = a
            a = y"""))

        ssa_code = SsaCode(as_tree)
        expected_ssa_dict = {'z': [0, 1, 2], 'a': [0, 1], 'y': [0]}
        self.assertEqual(str(ssa_code), ms("""\
        z_0 = a_0 Add y_0
        z_1 = a_0 Add y_0
        z_2 = a_0
        a_1 = y_0
        """))

        self.assertVariableVersionStack(ssa_code.var_version_list, expected_ssa_dict)

    def test_ssa_all_valid_expressions(self):
        as_tree = ast.parse(ms("""\
           a = b + c
           d = 2 * e
           f = g / 3
           h = - 4
           i = + j
           k = 1 < 3
           l = k | m
           n = o ^ 2""")
        )

        ssa_code = SsaCode(as_tree)

        self.assertEqual(str(ssa_code), ms("""\
        a_0 = b_0 Add c_0
        d_0 = 2 Mult e_0
        f_0 = g_0 Div 3
        h_0 = USub 4
        i_0 = UAdd j_0
        k_0 = 1 Lt 3
        l_0 = k_0 BitOr m_0
        n_0 = o_0 BitXor 2
        """))

    def test_ssa_repeated_expression(self):
        as_tree = ast.parse(ms("""\
            c = d + e
            e = 5
            d = d + e
            d = d + e
            c = d + e
            c = d + e""")
        )

        ssa_code = SsaCode(as_tree)
        self.assertEqual(str(ssa_code), ms("""\
            c_0 = d_0 Add e_0
            e_1 = 5
            d_1 = d_0 Add e_1
            d_2 = d_1 Add e_1
            c_1 = d_2 Add e_1
            c_2 = d_2 Add e_1
        """))
