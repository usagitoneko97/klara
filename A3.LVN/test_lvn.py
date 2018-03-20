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
        self.assertEqual(lvn_test.lvnDict['b'], 0)

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
        self.assertEqual(lvn_test.lvnDict['b'], 0)
        self.assertEqual(lvn_test.lvnDict['c'], 1)
        self.assertEqual(lvn_test.lvnDict['a'], 2)
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
        self.assertEqual(lvn_test.lvnDict['b'], 2)
        self.assertEqual(lvn_test.lvnDict['c'], 1)

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
        self.assertEqual(lvn_test.lvnDict['b'], 0)
        self.assertEqual(lvn_test.lvnDict['c'], 1)
        self.assertEqual(lvn_test.lvnDict['a'], 2)
        self.assertEqual(lvn_test.lvnDict['d'], 3)

        self.assertTrue('0Add1' in lvn_test.lvnDict)
        self.assertTrue(isinstance(optimized_tree.body[3].value, ast.Name))
        self.assertEqual(optimized_tree.body[3].value.id, "a")
        source = astor.to_source(optimized_tree)
        print(source)
        # check the ast




