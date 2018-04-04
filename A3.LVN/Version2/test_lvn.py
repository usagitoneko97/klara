import unittest
import ast
from common import *

from ssa import SsaCode
from lvn_dict import LvnDict, LvnStatement
from lvn import Lvn


class TestLvnDict(unittest.TestCase):
    def assert_lvn_stmt_list(self, lvn_stmt_list, *args):
        for i in range(len(args)):
            self.assert_lvn_stmt(lvn_stmt_list[i], args[i], "index {}".format(i))
        pass

    def assert_lvn_stmt(self, lvn_stmt, expression_tuple, msg):
        self.assertEqual(lvn_stmt.target, expression_tuple[0], "fail at " + msg + ': Target')
        self.assertEqual(lvn_stmt.left, expression_tuple[1], "fail at " + msg + ': Left operand')
        self.assertEqual(lvn_stmt.operator, expression_tuple[2], "fail at " + msg + ': Operator')
        self.assertEqual(lvn_stmt.right, expression_tuple[3], "fail at " + msg + ': Right operand')

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
        self.assertEqual(is_num(3), True)
        self.assertEqual(is_num(3.023), True)
        self.assertEqual(is_num("str"), False)

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

        expected_value_dict = {'a_0': 1, 'a_1': 3, 'a_2': 5, 'b_0': 4, 'c_0': 6,
                               'a_3': 7, 'd_0': 8, 'a_4': 9, '3': 0, '4': 2}
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

        expected_value_dict = {'a_0': 2, 'x_0': 0, 'y_0': 1, 'b_0': 3, '2': 4,
                               'a_1': 5, 'c_0': 6, '3': 7, 'd_0': 8, '4': 9,
                               'f_0': 10}
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

        expected_list = ['x_0', 'y_0', 'a_0', 'z_0', 'b_0', '2', 'a_1']
        self.assertListEqual(lvn_dict.variable_dict.val_num_var_list, expected_list)

# ----------------get_lvn_stmt test----------------------------------

    def test_get_lvn_stmt_all_possibilities(self):
        as_tree = ast.parse(ms("""\
           a = b + 4    # 2 = 0 + 1
           c = 33 + d   # 5 = 3 + 4
           e = f + g    # 8 = 6 + 7
           h = 24       # ...
           i = j
           k = - 38
           l = - m
           """)
        )

        ssa_code = SsaCode(as_tree)
        lvn_dict = LvnDict()
        lvn_stmt_list = []
        for ssa in ssa_code:
            lvn_dict.variable_dict.enumerate(ssa)
            lvn_stmt = lvn_dict.get_lvn_stmt(ssa)
            lvn_stmt_list.append(lvn_stmt)

        expected_lvn_stmt_list = [(2, 0, 'Add', 1),
                                  (5, 3, 'Add', 4),
                                  (8, 6, 'Add', 7),
                                  (10, 9, None, None),
                                  (12, 11, None, None),
                                  (14, None, 'USub', 13),
                                  (16, None, 'USub', 15)]

        self.assert_lvn_stmt_list(lvn_stmt_list, *expected_lvn_stmt_list)

    def test_get_lvn_stmt(self):
        as_tree = ast.parse(ms("""\
            c = b      # 1 = 0
            a = c + d  # 3 = 1 + 2
            """)
        )

        ssa_code = SsaCode(as_tree)
        lvn_dict = LvnDict()
        lvn_stmt_list = []
        for ssa in ssa_code:
            lvn_dict.variable_dict.enumerate(ssa)
            lvn_stmt = lvn_dict.get_lvn_stmt(ssa)
            lvn_stmt_list.append((lvn_stmt))

        expected_lvn_stmt_list = [(1, 0, None, None),
                                  (3, 1, 'Add', 2)]

        self.assert_lvn_stmt_list(lvn_stmt_list, *expected_lvn_stmt_list)

    def test_get_lvn_stmt_given_const(self):
        as_tree = ast.parse(ms("""\
            c = 33      # 1 = 0
            a = c + d   # 3 = 1 + 2
            """)
        )

        ssa_code = SsaCode(as_tree)
        lvn_dict = LvnDict()
        lvn_stmt_list = []
        for ssa in ssa_code:
            lvn_dict.variable_dict.enumerate(ssa)
            lvn_stmt = lvn_dict.get_lvn_stmt(ssa)
            lvn_stmt_list.append((lvn_stmt))

        expected_lvn_stmt_list = [(1, 0, None, None),
                                  (3, 1, 'Add', 2)]

        self.assert_lvn_stmt_list(lvn_stmt_list, *expected_lvn_stmt_list)

# ----------------------------reorder_selected_operands test-----------------
    def test_reorder_selected_operands(self):
        # 2 = 0 + 1 and 2 = 1 + 0
        lvn_stmt1 = LvnStatement(2, 0, 'Add', 1)
        lvn_stmt2 = LvnStatement(2, 1, 'Add', 0)
        lvn_stmt1.reorder_selected_operands()
        lvn_stmt2.reorder_selected_operands()
        self.assertEqual(str(lvn_stmt1), str(lvn_stmt2))

        # 2 = 0 - 1 is not 2 = 1 - 0
        lvn_stmt1 = LvnStatement(2, 0, 'Sub', 1)
        lvn_stmt2 = LvnStatement(2, 1, 'Sub', 0)
        lvn_stmt1.reorder_selected_operands()
        lvn_stmt2.reorder_selected_operands()
        self.assertNotEqual(str(lvn_stmt1), str(lvn_stmt2))

        # 2 = 0 should be the same
        lvn_stmt1 = LvnStatement(2, 0, None, None)
        lvn_stmt1.reorder_selected_operands()
        lvn_stmt2 = LvnStatement(2, 0, None, None)
        self.assertEqual(str(lvn_stmt1), str(lvn_stmt2))

# -------------------------- is_simple_assignment test------------------------------
    def test_is_simple_expr(self):
        # 3 = 0 + 1
        lvn_stmt = LvnStatement(3, 0, 'Add', 1)
        self.assertFalse(lvn_stmt.is_simple_assignment())

        lvn_stmt = LvnStatement(3, 0, 'Add', 1)
        self.assertFalse(lvn_stmt.is_simple_assignment())

        lvn_stmt = LvnStatement(3, 0, None, None)
        self.assertTrue(lvn_stmt.is_simple_assignment())

    # ----------------update simple_assign_dict test---------------------
    def test_update_simp_assign_test(self):
        lvn_handler = Lvn()
        lvn_handler.lvn_dict.simple_assign_dict.update_simp_assgn(0, 1)
        expected_simp_assgn_dict = {0: 1}
        self.assertDictEqual(lvn_handler.lvn_dict.simple_assign_dict,
                             expected_simp_assgn_dict)

# ----------------------Simple Assign Dict find substitute test---------------------------------
    def test_simple_assign_find_substitute(self):
        lvn_handler = Lvn()
        self.assertEqual(lvn_handler.lvn_dict.simple_assign_dict.find_substitute(0), 0)
        lvn_handler.lvn_dict.simple_assign_dict.update_simp_assgn(0, 5)
        self.assertEqual(lvn_handler.lvn_dict.simple_assign_dict.find_substitute(0), 5)

# --------------------- lvn stmt get expr test----------------------
    def test_lvn_stmt_get_expr(self):
        stmt = LvnStatement(3, 0, 'Add', 1)
        expr = stmt.get_expr()
        self.assertEqual(expr, '0Add1')

# --------------------lvn dict find substitute test---------------------------
    def test_lvn_dict_find_substitute_given_dict_empty(self):
        lvn_handler = Lvn()
        # lvn_dict is empty
        lvn_stmt = LvnStatement(3, 0, 'Add', 1)
        lvn_stmt_result = lvn_handler.lvn_dict.find_substitute(lvn_stmt)

        expected_lvn_stmt_tuple = (3, 0, 'Add', 1)
        self.assert_lvn_stmt(lvn_stmt_result, expected_lvn_stmt_tuple, "0")

    def test_lvn_dict_find_substitute_found_substitute(self):
        lvn_handler = Lvn()
        lvn_handler.lvn_dict["0Add1"] = 2

        lvn_stmt = LvnStatement(3, 0, 'Add', 1)
        lvn_stmt_result = lvn_handler.lvn_dict.find_substitute(lvn_stmt)

        expected_lvn_stmt_tuple = (3, 2, None, None)
        self.assert_lvn_stmt(lvn_stmt_result, expected_lvn_stmt_tuple, "0")

    def test_lvn_dict_find_substitute_given_simple_expr(self):
        lvn_handler = Lvn()
        lvn_handler.lvn_dict["0 + 1"] = 2

        # 3 = 0
        lvn_stmt = LvnStatement(3, 0, None, None)
        lvn_stmt_result = lvn_handler.lvn_dict.find_substitute(lvn_stmt)

        expected_lvn_stmt_tuple = (3, 0, None, None)
        self.assert_lvn_stmt(lvn_stmt_result, expected_lvn_stmt_tuple, "0")

        # 3 = 0 (0 is constant)
        lvn_stmt = LvnStatement(3, 0, None, None)
        lvn_stmt_result = lvn_handler.lvn_dict.find_substitute(lvn_stmt)

        expected_lvn_stmt_tuple = (3, 0, None, None)
        self.assert_lvn_stmt(lvn_stmt_result, expected_lvn_stmt_tuple, "0")

    # ---------------- lvn_code_tuples_list append lvn stmt test----------------------
    def test_lvn_code_tuple_list_append_lvn_stmt(self):
        lvn_handler = Lvn()
        lvn_stmt = LvnStatement(3, 0, 'Add', 1)
        lvn_handler.lvn_dict.lvn_code_tuples_list.append_lvn_stmt(lvn_stmt)
        expected_lvn_code_tup_list = [(3, 0, 'Add', 1)]

        self.assertTupleEqual(lvn_handler.lvn_dict.lvn_code_tuples_list[0],
                              expected_lvn_code_tup_list[0])

    # -------------lvn code to ssa test------------------------------
    def test_lvn_code_tuples_to_ssa_code(self):
        """
        a = x + y
        b = 2
        """
        lvn = Lvn()

        lvn.lvn_dict.lvn_code_tuples_list = [(2, 0, "Add", 1),
                                             (4, 3, None, None)]

        lvn.lvn_dict.variable_dict.val_num_var_list = ['x', 'y', 'a', '2', 'b']

        ssa_code = lvn.lvn_code_to_ssa_code()

        self.assertEqual(str(ssa_code), ms("""\
            a = x + y
            b = 2
            """))

    # ----------------optimize test--------------------------------------
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
            a_0 = x_0 + y_0
            b_0 = a_0
            a_1 = 17
            c_0 = a_0
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
            a_0 = x_0 + y_0
            b_0 = a_0
            x_1 = 98
            c_0 = y_0 + 98
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
            c_0 = d_0 + e_0
            e_1 = 5
            d_1 = d_0 + 5
            d_2 = 5 + d_1
            c_1 = 5 + d_2
            c_2 = c_1
            """))

    def test_optimize_code_with_bin_op(self):
        as_tree = ast.parse(ms("""\
            f = g | h
            k = g | j"""))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        self.assertEqual(str(ssa_code), ms("""\
            f_0 = g_0 | h_0
            k_0 = g_0 | j_0
            """))

    def test_optimize_code_with_xor(self):
        as_tree = ast.parse(ms("""\
            f = g ^ 33
            k = g ^ h"""))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        self.assertEqual(str(ssa_code), ms("""\
            f_0 = g_0 ^ 33
            k_0 = g_0 ^ h_0
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
            c_0 = d_0 + e_0
            d_1 = c_0
            f_0 = g_0 | h_0
            i_0 = s_0 ^ 3
            k_0 = f_0
            p_0 = i_0
            q_0 = 3 < x_0
            l_0 = q_0
            """))

    def test_optimize_code_with_2_lvn_stmt_same_expect_not_updated(self):
        as_tree = ast.parse(ms("""\
            f = g + j # 0 + 1
            k = g + 1 """))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        self.assertEqual(str(ssa_code), ms("""\
            f_0 = g_0 + j_0
            k_0 = g_0 + 1
            """))

    def test_optimize_simple_assignment_expect_substitute_single_var(self):
        as_tree = ast.parse(ms("""\
              a = b
              c = a"""))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        self.assertEqual(str(ssa_code), ms("""\
              a_0 = b_0
              c_0 = b_0
              """))

    def test_optimize_simple_assignment_given_all_possible_combination(self):
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
              z_0 = l_0
              a_0 = x_0 + y_0
              b_0 = 33
              c_0 = y_0 + 11
              d_0 = 34 + f_0
              """))

    def test_optimize_simple_assignment_expect_substituted(self):
        as_tree = ast.parse(ms("""\
              z = a + y
              b = a
              c = b
              d = c + y"""))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        self.assertEqual(str(ssa_code), ms("""\
              z_0 = a_0 + y_0
              b_0 = a_0
              c_0 = a_0
              d_0 = z_0
              """))

    def test_optimize_simple_assignment_given_constant(self):
        as_tree = ast.parse(ms("""\
              a = 33 + y
              b = 33
              c = b
              d = c + y"""))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        self.assertEqual(str(ssa_code), ms("""\
              a_0 = 33 + y_0
              b_0 = 33
              c_0 = 33
              d_0 = a_0
              """))

    def test_optimize_simple_assignment_given_constant_with_val_number_same_with_var(self):
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
              a_0 = x_0 + 1
              b_0 = a_0
              c_0 = a_0
              d_0 = x_0 + a_0
              """))

    def test_optimize_simple_assignment_expect_substituted_4_lines(self):
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
              k_0 = x_0 + y_0
              z_0 = k_0 + h_0
              a_0 = k_0
              b_0 = k_0
              c_0 = k_0
              d_0 = z_0
              """))

    def test_optimize_simple_assignment_given_3_stmt_same(self):
        as_tree = ast.parse(ms("""\
              a=3
              b=a
              c=b"""))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        print(ssa_code)
        self.assertEqual(str(ssa_code), ms("""\
              a_0 = 3
              b_0 = 3
              c_0 = 3
              """))

    def test_optimize_reordering_operands_Add_op(self):
        as_tree = ast.parse(ms("""\
            a = b + c
            d = c + b"""))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        self.assertEqual(str(ssa_code), ms("""\
            a_0 = b_0 + c_0
            d_0 = a_0
            """))

    def test_optimize_reordering_operands_BitOr_op(self):
        as_tree = ast.parse(ms("""\
            a = b | c
            d = c | b"""))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        self.assertEqual(str(ssa_code), ms("""\
            a_0 = b_0 | c_0
            d_0 = a_0
            """))

    def test_optimize_reordering_operands_Sub_op_expect_no_subs(self):
        as_tree = ast.parse(ms("""\
            a = b - c
            d = c - b"""))
        lvn_test = Lvn()
        ssa_code = SsaCode(as_tree)
        ssa_code = lvn_test.optimize(ssa_code)

        self.assertEqual(str(ssa_code), ms("""\
            a_0 = b_0 - c_0
            d_0 = c_0 - b_0
            """))



