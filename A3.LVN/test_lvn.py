import unittest
from lvn import Lvn
from tac import Tac
import ast
import astor

import textwrap

ms = textwrap.dedent


class TestValueAssign(unittest.TestCase):
    def assert_source_generated(self, as_tree, source_string):
        generated_string = astor.to_source(as_tree)
        self.assertEqual(generated_string, source_string, "source generated does not matched with expected source")

    def test_valueAssignToVar_1_stmt(self):
        """
        example:
            b = 2
        """
        ast_tree = ast.parse("b = 2")
        lvn_test = Lvn()
        lvn_test.lvn_optimize(ast_tree)
        self.assertEqual(lvn_test.value_number_dict['b'], 0)

    def test_valueAssignToVar_0_1(self):
        ast_tree = ast.parse(ms("""\
            b = 2
            c = 3
            a = b + c"""))
        lvn_test = Lvn()
        lvn_test.lvn_optimize(ast_tree)

        # Expected value
        expected_value_dict = {'b': 0, 'c': 1, 'a': 2}
        expected_assign_dict = {'0Add1': 2}

        self.assertDictEqual(expected_value_dict, lvn_test.value_number_dict)
        self.assertDictEqual(expected_assign_dict, lvn_test.lvnDict)

    def test_valueAssignToVar_updateVal(self):
        ast_tree = ast.parse(ms("""\
            b = 2
            c = 3
            b = 4"""))

        lvn_test = Lvn()
        lvn_test.lvn_optimize(ast_tree)

        expected_value_dict = {'b': 2, 'c': 1}
        self.assertDictEqual(expected_value_dict, lvn_test.value_number_dict)

    def test_valueAssignToVar_expect_replace_b_add_c_with_a(self):
        ast_tree = ast.parse(ms("""\
            a = b + c
            d = b + c"""))

        lvn_test = Lvn()
        optimized_tree = lvn_test.lvn_optimize(ast_tree)

        expected_value_dict = {'b': 0, 'c': 1, 'a': 2, 'd': 3}
        expected_assign_dict = {'0Add1': 2}

        self.assertDictEqual(expected_value_dict, lvn_test.value_number_dict)
        self.assertDictEqual(expected_assign_dict, lvn_test.lvnDict)

        self.assert_source_generated(optimized_tree, ms("""\
            a = b + c
            d = a
            """))

    def test_optimized_tree_given_var_add_const_expect_not_substituted(self):
        ast_tree = ast.parse(ms("""\
            a = b + 25
            d = b + 24"""))
        lvn_test = Lvn()
        optimized_tree = lvn_test.lvn_optimize(ast_tree)

        expected_value_dict = {'b': 0, '25': 1, 'a': 2, '24': 3, 'd': 4}
        expected_assign_dict = {'0Add1': 2, '0Add3': 4}

        self.assertDictEqual(expected_value_dict, lvn_test.value_number_dict)
        self.assertDictEqual(expected_assign_dict, lvn_test.lvnDict)

        self.assert_source_generated(optimized_tree, ms("""\
            a = b + 25
            d = b + 24
            """))

    def test_optimize_tree_given_var_add_const_expect_substituted(self):
        ast_tree = ast.parse(ms("""\
            a = b + 12
            d = b + 12"""))
        lvn_test = Lvn()
        optimized_tree = lvn_test.lvn_optimize(ast_tree)

        expected_value_dict = {'b': 0, '12': 1, 'a': 2, 'd': 3}
        expected_assign_dict = {'0Add1': 2}

        self.assertDictEqual(expected_value_dict, lvn_test.value_number_dict)
        self.assertDictEqual(expected_assign_dict, lvn_test.lvnDict)

        self.assert_source_generated(optimized_tree, ms("""\
            a = b + 12
            d = a
            """))

    def test_valueAssignToVar_expect_notUpdated(self):
        ast_tree = ast.parse(ms("""\
            a = x + y
            b = x + y
            a = 17
            c = x + y"""))
        lvn_test = Lvn()
        optimized_tree = lvn_test.lvn_optimize(ast_tree)

        expected_value_dict = {'a': 4, 'b': 3, 'c': 5, 'x': 0, 'y': 1}
        expected_assign_dict = {'0Add1': 2}

        self.assertDictEqual(expected_value_dict, lvn_test.value_number_dict)
        self.assertDictEqual(expected_assign_dict, lvn_test.lvnDict)

        self.assert_source_generated(optimized_tree, ms("""\
            a = x + y
            b = a
            a = 17
            c = x + y
            """))

    def test_valueAssignToVar_commutative(self):
        ast_tree = ast.parse(ms("""\
            a  = x * y
            b = y * x"""))
        lvn_test = Lvn()
        optimized_tree = lvn_test.lvn_optimize(ast_tree)

        expected_value_dict = {'a': 2, 'b': 3, 'x': 0, 'y': 1}
        expected_assign_dict = {'0Mult1': 2}

        self.assertDictEqual(expected_value_dict, lvn_test.value_number_dict)
        self.assertDictEqual(expected_assign_dict, lvn_test.lvnDict)

        self.assert_source_generated(optimized_tree, ms("""\
            a = x * y
            b = a
            """))

    def test_valueAssignToVar_commutative_minus_operation(self):
        ast_tree = ast.parse(ms("""\
            a = x - y
            b = y - x""")
        )
        lvn_test = Lvn()
        optimized_tree = lvn_test.lvn_optimize(ast_tree)

        expected_value_dict = {'a': 2, 'b': 3, 'x': 0, 'y': 1}
        expected_assign_dict = {'0Sub1': 2, '1Sub0': 3}

        self.assertDictEqual(expected_value_dict, lvn_test.value_number_dict)
        self.assertDictEqual(expected_assign_dict, lvn_test.lvnDict)

        self.assert_source_generated(optimized_tree, ms("""\
            a = x - y
            b = y - x
            """))

    def test_alg_identities_a_add_0(self):
        ast_tree = ast.parse(ms("""\
            b = a + 0
            c = 0 + a""")
        )
        lvn_test = Lvn()
        optimized_tree = lvn_test.lvn_optimize(ast_tree)

        expected_value_dict = {'a': 0, '0': 1, 'b': 2, 'c': 3}

        self.assertDictEqual(expected_value_dict, lvn_test.value_number_dict)

        self.assert_source_generated(optimized_tree, ms("""\
            b = a
            c = a
            """))

    def test_alg_identities_a_min_a_0(self):
        ast_tree = ast.parse(ms("""\
                    b = a - 0""")
                             )
        lvn_test = Lvn()
        optimized_tree = lvn_test.lvn_optimize(ast_tree)

        expected_value_dict = {'a': 0, '0': 1, 'b': 2}

        self.assertDictEqual(expected_value_dict, lvn_test.value_number_dict)

        self.assert_source_generated(optimized_tree, ms("""\
                    b = a
                    """))

    def test_alg_identities_a_mult_0_0(self):
        ast_tree = ast.parse(ms("""\
                    b = a * 0""")
                             )
        lvn_test = Lvn()
        optimized_tree = lvn_test.lvn_optimize(ast_tree)

        expected_value_dict = {'a': 0, '0': 1, 'b': 2}

        self.assertDictEqual(expected_value_dict, lvn_test.value_number_dict)

        self.assert_source_generated(optimized_tree, ms("""\
                    b = 0
                    """))

    def test_alg_identities_a_add_a_2a(self):
        ast_tree = ast.parse(ms("""\
            b = a + a
            c = a * 2""")
        )
        lvn_test = Lvn()
        optimized_tree = lvn_test.lvn_optimize(ast_tree)

        expected_value_dict = {'a': 0, 'b': 1, 'c': 3, '2': 2}
        expected_assign_dict = {'0Add0': 1}

        self.assertDictEqual(expected_value_dict, lvn_test.value_number_dict)
        self.assertDictEqual(expected_assign_dict, lvn_test.lvnDict)

        self.assert_source_generated(optimized_tree, ms("""\
            b = a + a
            c = b
            """))

    def test_alg_identities_a_add_a_expect_substituted(self):
        ast_tree = ast.parse(ms("""\
                    b = a + a
                    c = a + a""")
                             )
        lvn_test = Lvn()
        optimized_tree = lvn_test.lvn_optimize(ast_tree)

        expected_value_dict = {'a': 0, 'b': 1, 'c': 2}
        expected_assign_dict = {'0Add0': 1}

        self.assertDictEqual(expected_value_dict, lvn_test.value_number_dict)
        self.assertDictEqual(expected_assign_dict, lvn_test.lvnDict)

        self.assert_source_generated(optimized_tree, ms("""\
                    b = a + a
                    c = b
                    """))

    def xtest_problems_redefining(self):
        """
                        input:            expected output
                        a = x + y         a = x + y
                        b = x + y         b = a
                        a = 17            a = 17
                        c = x + y         c = b
                        """
        ast_tree = ast.parse(ms("""\
                                             a = x + y
                                             b = x + y
                                             a = 17
                                             c = x + y"""))
        print(astor.to_source(ast_tree))
        lvn_test = Lvn()
        optimized_tree = lvn_test.lvn_optimize(ast_tree)
        # self.assertEqual(lvn_test.value_number_dict['x'], 0)
        # self.assertEqual(lvn_test.value_number_dict['y'], 1)
        # self.assertEqual(lvn_test.value_number_dict['a'], 2)
        # self.assertEqual(lvn_test.value_number_dict['b'], 3)
        #
        # self.assertTrue('0Sub1' in lvn_test.lvnDict)
        # self.assertTrue(not isinstance(optimized_tree.body[3].value, ast.Name))
        self.assert_source_generated(optimized_tree, ms("""\
                                                                     a = x + y
                                                                     b = a
                                                                     a = 17
                                                                     c = b
                                                                     """))

    def test_lvn_ast2arg_expr_given_a_plus_3(self):
        as_tree = ast.parse(ms("""\
                    b = a + 3""")
                             )

        expr_str = Lvn.lvn_ast2arg_expr(as_tree.body[0])
        self.assertEqual(expr_str, "#Add3")

    def test_lvn_ast2arg_expr_given_3_plus_3(self):
        as_tree = ast.parse(ms("""\
                            b = 3 + 3""")
                            )

        expr_str = Lvn.lvn_ast2arg_expr(as_tree.body[0])
        self.assertEqual(expr_str, "3Add3")

    def test_lvn_ast2arg_expr_given_a_plus_a(self):
        as_tree = ast.parse(ms("""\
                            b = a + a""")
                            )

        expr_str = Lvn.lvn_ast2arg_expr(as_tree.body[0])
        self.assertEqual(expr_str, "#Add#")

    def test_lvn_ast2arg_expr_given_a_plus_c(self):
        as_tree = ast.parse(ms("""\
                            b = a + c""")
                            )

        expr_str = Lvn.lvn_ast2arg_expr(as_tree.body[0])
        self.assertEqual(expr_str, "#Add_")

    def test_lvn_ast2arg_expr_given_3_add_a_expect_reorder(self):
        as_tree = ast.parse(ms("""\
                            b = 3 + a""")
                            )

        expr_str = Lvn.lvn_ast2arg_expr(as_tree.body[0])
        self.assertEqual(expr_str, "#Add3")

    def test_tac(self):
        as_tree = ast.parse(ms("""\
                            b = 3 + a""")
                            )

        b_stmt = Tac(as_tree.body[0])

        b_stmt.target = 'd'
