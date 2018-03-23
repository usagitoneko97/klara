import unittest
from lvn import Lvn
import ast
import astor

import textwrap


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
        """
        example:
            b = 2
            |
            0
            c = 3
            |
            1
            a = b + c
            |   |   |
            2   0   1
        """
        ast_tree = ast.parse(textwrap.dedent("""\
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
        """
        example:
            b = 2
            |
            0

            c = 3
            |
            1

            b = 4
            |
            2
        """
        ast_tree = ast.parse(textwrap.dedent("""\
                                b = 2
                                c = 3
                                b = 4"""))

        lvn_test = Lvn()
        lvn_test.lvn_optimize(ast_tree)

        expected_value_dict = {'b': 2, 'c': 1}
        self.assertDictEqual(expected_value_dict, lvn_test.value_number_dict)

    def test_valueAssignToVar_expect_replace_b_add_c_with_a(self):
        """
        example:
            b = 2
            |
            0
            c = 3
            |
            1
            a = b + c
            |   |   |
            2   0   1
            d = b + c          d = a
            |   |   |   ---->
            3   0   1
        """
        ast_tree = ast.parse(textwrap.dedent("""\
                                    b = 2
                                    c = 3
                                    a = b + c
                                    d = b + c"""))

        lvn_test = Lvn()
        optimized_tree = lvn_test.lvn_optimize(ast_tree)

        expected_value_dict = {'b': 0, 'c': 1, 'a': 2, 'd': 3}
        expected_assign_dict = {'0Add1': 2}

        self.assertDictEqual(expected_value_dict, lvn_test.value_number_dict)
        self.assertDictEqual(expected_assign_dict, lvn_test.lvnDict)

        self.assert_source_generated(optimized_tree, textwrap.dedent("""\
                                                                b = 2
                                                                c = 3
                                                                a = b + c
                                                                d = a
                                                                """))
        # check the ast

    def test_valueAssignToVar_expect_notUpdated(self):
        """
        example:
           a = x + y                            a = x + y
           b = x + y                     -->>   b = a
           a = 17                               a = 17
           c = x + y                            c = x + y  -- not updated
        """
        ast_tree = ast.parse(textwrap.dedent("""\
                                 x = 2
                                 y = 3
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

        self.assert_source_generated(optimized_tree, textwrap.dedent("""\
                                                                 x = 2
                                                                 y = 3
                                                                 a = x + y
                                                                 b = a
                                                                 a = 17
                                                                 c = x + y
                                                                 """))
        # check the ast

    def test_valueAssignToVar_commutative(self):
        """
        input:            expected output
        a = x + y         a = x + y
        b = y + x         b = a
        """
        ast_tree = ast.parse(textwrap.dedent("""\
                                x = 2
                                y = 3
                                a = x * y
                                b = y * x"""))
        lvn_test = Lvn()
        optimized_tree = lvn_test.lvn_optimize(ast_tree)

        expected_value_dict = {'a': 2, 'b': 3, 'x': 0, 'y': 1}
        expected_assign_dict = {'0Mult1': 2}

        self.assertDictEqual(expected_value_dict, lvn_test.value_number_dict)
        self.assertDictEqual(expected_assign_dict, lvn_test.lvnDict)

        self.assert_source_generated(optimized_tree, textwrap.dedent("""\
                                                                     x = 2
                                                                     y = 3
                                                                     a = x * y
                                                                     b = a
                                                                     """))

    def test_valueAssignToVar_commutative_minus_operation(self):
        """
                input:            expected output
                a = x - y         a = x - y
                b = y - x         b = y - x
                """

        ast_tree = ast.parse(textwrap.dedent("""\
                                x = 2
                                y = 3
                                a = x - y
                                b = y - x""")
        )
        lvn_test = Lvn()
        optimized_tree = lvn_test.lvn_optimize(ast_tree)

        expected_value_dict = {'a': 2, 'b': 3, 'x': 0, 'y': 1}
        expected_assign_dict = {'0Sub1': 2, '1Sub0': 3}

        self.assertDictEqual(expected_value_dict, lvn_test.value_number_dict)
        self.assertDictEqual(expected_assign_dict, lvn_test.lvnDict)

        self.assert_source_generated(optimized_tree, textwrap.dedent("""\
                                                                    x = 2
                                                                    y = 3
                                                                    a = x - y
                                                                    b = y - x
                                                                     """))

    def xtest_problems_redefining(self):
        """
                        input:            expected output
                        a = x + y         a = x + y
                        b = x + y         b = a
                        a = 17            a = 17
                        c = x + y         c = b
                        """
        ast_tree = ast.parse(textwrap.dedent("""\
                                x = 2
                                y = 3
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
        self.assert_source_generated(optimized_tree, textwrap.dedent("""\
                                                                     x = 2
                                                                     y = 3
                                                                     a = x + y
                                                                     b = a
                                                                     a = 17
                                                                     c = b
                                                                     """))