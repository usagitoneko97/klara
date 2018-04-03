import unittest
import ast
from common import *

from ssa import SsaCode
from lvn_dict import LvnDict, LvnExpression
from lvn import Lvn



class TestLvnDict(unittest.TestCase):
    def assert_lvn_expression_list(self, lvn_expression_list, *args):
        for i in range(len(args)):
            self.assert_lvn_expression(lvn_expression_list[i], args[i], "index {}".format(i))
        pass

    def assert_lvn_expression(self, lvn_expression, expression_tuple, msg):
        self.assertEqual(lvn_expression.operand_type, expression_tuple[4], "fail at " + msg + ': Operand type')
        self.assertEqual(lvn_expression.target, expression_tuple[0], "fail at " + msg + ': Target')
        self.assertEqual(lvn_expression.left, expression_tuple[1], "fail at " + msg + ': Left operand')
        self.assertEqual(lvn_expression.operator, expression_tuple[2], "fail at " + msg + ': Operator')
        self.assertEqual(lvn_expression.right, expression_tuple[3], "fail at " + msg + ': Right operand')

    def assert_ssa(self, ssa, target, left_oprd, right_oprd, operator=None):
        self.assertEqual(ssa.target, target)
        self.assertEqual(ssa.left_oprd, left_oprd)
        self.assertEqual(ssa.right_oprd, right_oprd)

        if operator is not None:
            self.assertEqual(ssa.operator, operator)

    def assert_ssa_list(self, ssa_list, target_list, left_oprd_list, right_oprd_list, operator_list=None):
        for i in range(len(ssa_list)):
            if operator_list is not None:
                self.assert_ssa(ssa_list[i], target_list[i], left_oprd_list[i], right_oprd_list[i], operator_list[i])
            else:
                self.assert_ssa(ssa_list[i], target_list[i], left_oprd_list[i], right_oprd_list[i], None)

    def test_is_num(self):
        self.assertEqual(common.is_num(3), True)
        self.assertEqual(common.is_num(3.023), True)
        self.assertEqual(common.is_num("str"), False)

# ----------------------------Enumerate test-----------------------------------
    def test_enumerate_given_multiple_time(self):
        as_tree = ast.parse(ms("""\
            a = 3   # a = 0
            a = 4   # a = 1
            a = b   # b = 2, a = 3
            a = c   # c = 4, a = 5
            a = d   # d = 6, a = 7
            """)
        )

        ssa_code = SsaCode(as_tree)
        lvn_dict = LvnDict()
        for ssa in ssa_code:
            lvn_dict.variable_dict.enumerate(ssa)

        expected_value_dict = {'a_0': 0, 'a_1': 1, 'a_2': 3, 'b_0': 2, 'c_0': 4, 'a_3': 5, 'd_0': 6, 'a_4': 7}
        self.assertDictEqual(lvn_dict.variable_dict, expected_value_dict)

    def test_enumerate_given_a_update(self):
        as_tree = ast.parse(ms("""\
                               a = x + y
                               b = x + y
                               a = 2
                               c = x + y
                               d = 3 + x
                               f = y + 4""")
                            )

        ssa_code = SsaCode(as_tree)
        lvn_dict = LvnDict()
        for ssa in ssa_code:
            lvn_dict.variable_dict.enumerate(ssa)

        expected_value_dict = {'a_0': 2, 'x_0': 0, 'y_0': 1, 'b_0': 3, 'a_1': 4, 'c_0': 5, 'd_0': 6, 'f_0': 7}
        self.assertDictEqual(lvn_dict.variable_dict, expected_value_dict)

    def test_value_number_to_var_list(self):
        as_tree = ast.parse(ms("""\
               a = x + y
               b = x - z
               a = 2""")
        )

        ssa_code = SsaCode(as_tree)
        lvn_dict = LvnDict()
        for ssa in ssa_code:
            lvn_dict.variable_dict.enumerate(ssa)

        expected_list = ['x_0', 'y_0', 'a_0', 'z_0', 'b_0', 'a_1']
        self.assertListEqual(lvn_dict.variable_dict.val_num_var_list, expected_list)

# ----------------get_lvn_expr test----------------------------------

    def test_get_lvn_expr(self):
        as_tree = ast.parse(ms("""\
           a = b + 4    # b = 0, a = 1
           c = 33 + d   # d = 2, c = 3
           e = f + g    # f = 4, g = 5, e = 6
           h = 24       # h = 7
           i = j        # j = 8, i = 9
           k = - 38     # k = 10
           l = - m      # m = 11, l = 12
           """)
        )

        ssa_code = SsaCode(as_tree)
        lvn_dict = LvnDict()
        lvn_expr_list = []
        for ssa in ssa_code:
            lvn_dict.variable_dict.enumerate(ssa)
            lvn_expr = lvn_dict.get_lvn_expr(ssa)
            lvn_expr_list.append((lvn_expr))

        expected_lvn_expr_list = [(1, 0, 'Add', 4, 2),
                                  (3, 33, 'Add', 2, 1),
                                  (6, 4, 'Add', 5, 0),
                                  (7, 24, None, None, 1),
                                  (9, 8, None, None, 0),
                                  (10, None, 'USub', 38, 2),
                                  (12, None, 'USub', 11, 0)]

        self.assert_lvn_expression_list(lvn_expr_list, *expected_lvn_expr_list)

    def test_get_lvn_expr(self):
        as_tree = ast.parse(ms("""\
            c = b
            a = c + d
            """)
        )

        ssa_code = SsaCode(as_tree)
        lvn_dict = LvnDict()
        lvn_expr_list = []
        for ssa in ssa_code:
            lvn_dict.variable_dict.enumerate(ssa)
            lvn_expr = lvn_dict.get_lvn_expr(ssa)
            lvn_expr_list.append((lvn_expr))

        expected_lvn_expr_list = [(1, 0, None, None, 0),
                                  (3, 1, 'Add', 2, 0)]

        self.assert_lvn_expression_list(lvn_expr_list, *expected_lvn_expr_list)

    def test_get_lvn_expr_given_const(self):
        as_tree = ast.parse(ms("""\
            c = 33
            a = c + d
            """)
        )

        ssa_code = SsaCode(as_tree)
        lvn_dict = LvnDict()
        lvn_expr_list = []
        for ssa in ssa_code:
            lvn_dict.variable_dict.enumerate(ssa)
            lvn_expr = lvn_dict.get_lvn_expr(ssa)
            lvn_expr_list.append((lvn_expr))

        expected_lvn_expr_list = [(0, 33, None, None, 1),
                                  (2, 0, 'Add', 1, 0)]

        self.assert_lvn_expression_list(lvn_expr_list, *expected_lvn_expr_list)

# -------------------------- is_simple_expr test------------------------------
    def test_is_simple_expr(self):
        # 3 = 0 + 1
        lvn_expr = LvnExpression(0, 1, 'Add', 3, 0)
        self.assertFalse(lvn_expr.is_simple_expr())

        lvn_expr = LvnExpression(0, 1, 'Add', 3, 1)
        self.assertFalse(lvn_expr.is_simple_expr())

        lvn_expr = LvnExpression(0, None, None, 3, 1)
        self.assertTrue(lvn_expr.is_simple_expr())

# ----------------------Simple Assign Dict find substitute test---------------------------------
    def test_simple_assign_find_substitute(self):
        lvn_handler = Lvn()
        self.assertEqual(lvn_handler.lvn_dict.simple_assign_dict.find_substitute(0), 0)
        lvn_handler.lvn_dict.simple_assign_dict.update_simp_assgn(0, 5)
        self.assertEqual(lvn_handler.lvn_dict.simple_assign_dict.find_substitute(0), 5)

# --------------------lvn dict find substitute test---------------------------
    def test_lvn_dict_find_substitute_found_substitute(self):
        lvn_handler = Lvn()
        lvn_handler.lvn_dict["0 + 1"] = [2, 0]

        lvn_expr = LvnExpression(0, 1, 'Add', 3, 0)
        lvn_expr_result = lvn_handler.find_substitute(lvn_expr)

        expected_lvn_expr_tuple = (3, 2, None, None, 0)
        self.assert_lvn_expression(lvn_expr_result, expected_lvn_expr_tuple)

    def test_lvn_dict_find_substitute_given_left_constant(self):
        lvn_handler = Lvn()
        lvn_handler.lvn_dict["0 + 1"] = [2, 0]

        lvn_expr = LvnExpression(0, 1, 'Add', 3, 1)
        lvn_expr_result = lvn_handler.find_substitute(lvn_expr)

        expected_lvn_expr_tuple = (3, 0, 'Add', 1, 1)
        self.assert_lvn_expression(lvn_expr_result, expected_lvn_expr_tuple)

    def test_build_lvn_expr_and_lvn_code_tuple(self):
        as_tree = ast.parse(ms("""\
                       a = x + y
                       b = x + z
                       a = 2""")
                            )

        ssa_code = SsaCode(as_tree)
        lvn_dict = LvnDict()
        for ssa in ssa_code:
            lvn_dict.enumerate_rhs(ssa)
            lvn_expr = lvn_dict.get_lvn_expr(ssa)
            lvn_dict.enumerate_lhs(ssa)
            lvn_dict.add_lvn_expr(lvn_expr)

        # Testing internal data
        expected_lvn_dict = {'0Add1': [2, 0], '0Add3': [4, 0]}
        self.assertEqual(lvn_dict, expected_lvn_dict)

        expected_lvn_code_tuples = [(2, 0, 'Add', 1, 0),
                                    (4, 0, 'Add', 3, 0),
                                    (5, 2, None, None, 1)]

        for i in range(len(expected_lvn_code_tuples)):
            self.assertTupleEqual(lvn_dict.lvn_code_tuples_list[i], expected_lvn_code_tuples[i])

    def test_lvn_code_tuples_to_ssa_code(self):
        """
        a = x + y
        b = 2
        """
        lvn = Lvn()

        lvn.lvn_dict.lvn_code_tuples_list = [(2, 0, "Add", 1, 0),
                                             (3, 2, None, None, 1)]

        lvn.lvn_dict.variable_dict.val_num_var_list = ['x', 'y', 'a', 'b']

        ssa_code = lvn.lvn_code_to_ssa_code()

        self.assertEqual(str(ssa_code), """a = x + y\nb = 2\n""")

    def test_optimize_code_with_variable_reassigned(self):
        """
        x gets redefined at 3rd statement, result in the 4th statement not optimized
        """
        as_tree = ast.parse(ms("""\
            d = d + e"""))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        # # Testing internal data
        # expected_value_dict = {'a': 4, 'b': 3, 'c': 5, 'x': 0, 'y': 1, 'a_2': 2}
        # expected_assign_dict = {'0Add1': 2}
        #
        # self.assertDictEqual(expected_value_dict, lvn_test.value_number_dict)
        # self.assertDictEqual(expected_assign_dict, lvn_test.lvnDict)

        # Test the output
        self.assertEqual(str(ssa_code), ms("""\
            d = d_0 + e
            """))

    def test_optimize_code_with_variable_redefinition_1(self):
        as_tree = ast.parse(ms("""\
            a = x + y
            b = x + y
            a = 17
            c = x + y"""))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        # Test the output
        self.assertEqual(str(ssa_code), ms("""\
            a_2 = x + y
            b = a_2
            a = 17
            c = a_2
            """))

    def test_optimize_code_with_variable_redefinition_2(self):
        """
        x gets redefined at 3rd statement, result in the 4th statement not optimized
        :return:
        """
        as_tree = ast.parse(ms("""\
            a = x + y
            b = x + y
            x = 98
            c = x + y"""))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        # Test the output
        self.assertEqual(str(ssa_code), ms("""\
            a = x_0 + y
            b = a
            x = 98
            c = x + y
            """))

    def test_optimize_code_with_variable_redefinition_expect_not_update(self):
        """
        x gets redefined at 3rd statement, result in the 4th statement not optimized
        :return:
        """
        as_tree = ast.parse(ms("""\
            c = d + e
            e = 5
            d = d + e
            d = d + e
            c = d + e
            c = d + e"""))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        self.assertEqual(str(ssa_code), ms("""\
            c_2 = d_0 + e_1
            e = 5
            d_4 = d_0 + e
            d = d_4 + e
            c_6 = d + e
            c = c_6
            """))

    def test_optimize_code_with_bin_op(self):
        as_tree = ast.parse(ms("""\
            f = g | h
            k = g | j"""))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        self.assertEqual(str(ssa_code), ms("""\
            f = g | h
            k = g | j
            """))

    def test_optimize_code_with_xor(self):
        as_tree = ast.parse(ms("""\
            f = g ^ 33
            k = g ^ h"""))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        self.assertEqual(str(ssa_code), ms("""\
            f = g ^ 33
            k = g ^ h
            """))

    def test_optimize_code_with_different_operator(self):
        as_tree = ast.parse(ms("""\
            c = d + e
            d = d + e
            f = g | h
            i = s ^ 3
            k = g | h
            p = s ^ 3
            q = 3 < x
            l = 3 < x"""))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        self.assertEqual(str(ssa_code), ms("""\
            c = d_0 + e
            d = c
            f = g | h
            i = s ^ 3
            k = f
            p = i
            q = 3 < x
            l = q
            """))

    def test_optimize_code_with_2_lvn_expr_same_expect_not_updated(self):
        as_tree = ast.parse(ms("""\
            f = g + j # 0 + 1
            k = g + 1 # 0 + 1"""))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        self.assertEqual(str(ssa_code), ms("""\
            f = g + j
            k = g + 1
            """))

    def test_simple_assignment_dict(self):
        # 1 = 0
        lvn_expr = LvnExpression(left=0, right=None, operator=None, target=1, operand_type=0)
        lvn_test = Lvn()
        lvn_test.lvn_dict.add_lvn_expr(lvn_expr)
        expected_simple_assign_dict = {1: [0, 0]}
        self.assertDictEqual(lvn_test.lvn_dict.simple_assign_dict, expected_simple_assign_dict)

        # 2 = 0 + 1
        lvn_expr = LvnExpression(left=0, right=1, operator='Add', target=2, operand_type=0)
        lvn_test = Lvn()
        lvn_test.lvn_dict.add_lvn_expr(lvn_expr)
        expected_simple_assign_dict = {}
        self.assertDictEqual(lvn_test.lvn_dict.simple_assign_dict, expected_simple_assign_dict)

        # 2 = 0 + 44 where 44 is constant
        lvn_expr = LvnExpression(left=0, right=44, operator='Add', target=2, operand_type=2)
        lvn_test = Lvn()
        lvn_test.lvn_dict.add_lvn_expr(lvn_expr)
        expected_simple_assign_dict = {}
        self.assertDictEqual(lvn_test.lvn_dict.simple_assign_dict, expected_simple_assign_dict)

        # 2 = 44 + 0
        lvn_expr = LvnExpression(left=44, right=0, operator='Add', target=2, operand_type=1)
        lvn_test = Lvn()
        lvn_test.lvn_dict.add_lvn_expr(lvn_expr)
        expected_simple_assign_dict = {}
        self.assertDictEqual(lvn_test.lvn_dict.simple_assign_dict, expected_simple_assign_dict)

        # 1 = 44
        lvn_expr = LvnExpression(left=44, right=None, operator=None, target=1, operand_type=1)
        lvn_test = Lvn()
        lvn_test.lvn_dict.add_lvn_expr(lvn_expr)
        expected_simple_assign_dict = {1: [44, 1]}
        self.assertDictEqual(lvn_test.lvn_dict.simple_assign_dict, expected_simple_assign_dict)

    def test_simple_assignment_expect_substitute_single_var(self):
        as_tree = ast.parse(ms("""\
            a = b
            c = a"""))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        self.assertEqual(str(ssa_code), ms("""\
            a = b
            c = b
            """))

    def test_simple_assignment_given_all_possible_combination(self):
        as_tree = ast.parse(ms("""\
            z = l
            a = x + y
            b = 33
            c = y + 11
            d = 34 + f"""))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        self.assertEqual(str(ssa_code), ms("""\
            z = l
            a = x + y
            b = 33
            c = y + 11
            d = 34 + f
            """))

    def test_simple_assignment_expect_substituted(self):
        as_tree = ast.parse(ms("""\
            z = a + y
            b = a
            c = b
            d = c + y"""))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        self.assertEqual(str(ssa_code), ms("""\
            z = a + y
            b = a
            c = a
            d = z
            """))

    def test_simple_assignment_given_constant(self):
        as_tree = ast.parse(ms("""\
            a = 33 + y
            b = 33
            c = b
            d = c + y"""))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        self.assertEqual(str(ssa_code), ms("""\
            a = 33 + y
            b = 33
            c = 33
            d = a
            """))

    def test_simple_assignment_given_constant_with_val_number_same_with_var(self):
        as_tree = ast.parse(ms("""\
            a = x + 1
            b = a
            c = b
            d = x + c # c will be replaced by 1, the simple expr is 0 + 1, but its diff than the first assignment (which
                      # is also 0 + 1 because the first statement is referring to constant 1 while fourth statement is
                      # referring to variable with value number 1
            """))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        self.assertEqual(str(ssa_code), ms("""\
            a = x + 1
            b = a
            c = a
            d = x + c
            """))

    def test_simple_assignment_expect_substituted_4_lines(self):
        as_tree = ast.parse(ms("""\
            k = x + y
            z = k + h
            a = x + y
            b = a
            c = b
            d = c + h"""))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        self.assertEqual(str(ssa_code), ms("""\
            k = x + y
            z = k + h
            a = k
            b = k
            c = k
            d = z
            """))

    def test_simple_assignment_given_3_stmt_same(self):
        as_tree = ast.parse(ms("""\
            a=3
            b=a
            c=b"""))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        print(ssa_code)
        self.assertEqual(str(ssa_code), ms("""\
            a = 3
            b = 3
            c = 3
            """))