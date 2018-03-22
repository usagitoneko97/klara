import unittest
from lvn import Lvn
import ast
import astor


class TestValueAssign(unittest.TestCase):
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
        ast_tree = ast.parse("b = 2\nc = 3\na = b + c\n")
        lvn_test = Lvn()
        lvn_test.lvn_optimize(ast_tree)
        self.assertEqual(lvn_test.value_number_dict['b'], 0)
        self.assertEqual(lvn_test.value_number_dict['c'], 1)
        self.assertEqual(lvn_test.value_number_dict['a'], 2)
        self.assertTrue('0Add1' in lvn_test.lvnDict)

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
        ast_tree = ast.parse("b = 2\nc = 3\nb = 4\n")

        lvn_test = Lvn()
        lvn_test.lvn_optimize(ast_tree)
        self.assertEqual(lvn_test.value_number_dict['b'], 2)
        self.assertEqual(lvn_test.value_number_dict['c'], 1)

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
        print("------start of 1st optimization test--------")
        ast_tree = ast.parse("b = 2\nc = 3\na = b + c\nd=b+c")
        print(astor.to_source(ast_tree))
        lvn_test = Lvn()
        optimized_tree = lvn_test.lvn_optimize(ast_tree)
        self.assertEqual(lvn_test.value_number_dict['b'], 0)
        self.assertEqual(lvn_test.value_number_dict['c'], 1)
        self.assertEqual(lvn_test.value_number_dict['a'], 2)
        self.assertEqual(lvn_test.value_number_dict['d'], 3)

        self.assertTrue('0Add1' in lvn_test.lvnDict)
        self.assertTrue(isinstance(optimized_tree.body[3].value, ast.Name))
        self.assertEqual(optimized_tree.body[3].value.id, "a")
        source = astor.to_source(optimized_tree)
        print(source)
        # check the ast

    def test_valueAssignToVar_expect_notUpdated(self):
        """
        example:
           a = x + y                            a = x + y
           b = x + y                     -->>   b = a
           a = 17                               a = 17
           c = x + y                            c = x + y  -- not updated
        """
        print("------start of 2nd optimization test--------")
        ast_tree = ast.parse("x = 2\ny = 3\na = x + y\nb=x+y\na=17\nc=x+y")
        print(astor.to_source(ast_tree))
        lvn_test = Lvn()
        optimized_tree = lvn_test.lvn_optimize(ast_tree)
        self.assertEqual(lvn_test.value_number_dict['a'], 4)
        self.assertEqual(lvn_test.value_number_dict['b'], 3)
        self.assertEqual(lvn_test.value_number_dict['c'], 5)

        self.assertTrue('0Add1' in lvn_test.lvnDict)
        self.assertTrue(isinstance(optimized_tree.body[3].value, ast.Name))
        self.assertEqual(optimized_tree.body[3].value.id, "a")
        source = astor.to_source(optimized_tree)
        print(source)
        # check the ast

    def test_valueAssignToVar_commutative(self):
        """
        input:            expected output
        a = x + y         a = x + y
        b = y + x         b = a
        """
        print("------start of 3rd optimization test--------")
        ast_tree = ast.parse("x = 2\ny = 3\na = x + y\nb=y+x")
        print(astor.to_source(ast_tree))
        lvn_test = Lvn()
        optimized_tree = lvn_test.lvn_optimize(ast_tree)
        self.assertEqual(lvn_test.value_number_dict['x'], 0)
        self.assertEqual(lvn_test.value_number_dict['y'], 1)
        self.assertEqual(lvn_test.value_number_dict['a'], 2)
        self.assertEqual(lvn_test.value_number_dict['b'], 3)

        self.assertTrue('0Add1' in lvn_test.lvnDict)
        self.assertTrue(isinstance(optimized_tree.body[3].value, ast.Name))
        self.assertEqual(optimized_tree.body[3].value.id, "a")
        source = astor.to_source(optimized_tree)
        print(source)