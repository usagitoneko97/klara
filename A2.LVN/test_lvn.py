import unittest
from lvn import lvn
import ast
import astor
class testValueAssign(unittest.TestCase):
    def test_valueAssignToVar_1_stmt(self):
        """
        example:
            b = 2
        """
        astTree = ast.parse("b = 2")
        lvnTest = lvn()
        lvnTest.assignValueNumber(astTree)
        self.assertEqual(lvnTest.valueDict['b'], 0)
        self.assertEqual(len(lvnTest.valueDict), 1)

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
        astTree = ast.parse("b = 2\nc = 3\na = b + c\n")
        lvnTest = lvn()
        lvnTest.assignValueNumber(astTree)
        self.assertEqual(lvnTest.valueDict['b'], 0)
        self.assertEqual(lvnTest.valueDict['c'], 1)
        self.assertEqual(lvnTest.valueDict['a'], 2)
        self.assertEqual(len(lvnTest.valueDict), 3)
        self.assertTrue('0Add1' in lvnTest.lvnDict)

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
        astTree = ast.parse("b = 2\nc = 3\nb = 4\n")

        lvnTest = lvn()
        lvnTest.assignValueNumber(astTree)
        self.assertEqual(lvnTest.valueDict['b'], 2)
        self.assertEqual(lvnTest.valueDict['c'], 1)
        self.assertEqual(len(lvnTest.valueDict), 2)

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
        astTree = ast.parse("b = 2\nc = 3\na = b + c\nd=b+c")
        print(astor.to_source(astTree))
        lvnTest = lvn()
        optimizedTree = lvnTest.assignValueNumber(astTree)
        self.assertEqual(lvnTest.valueDict['b'], 0)
        self.assertEqual(lvnTest.valueDict['c'], 1)
        self.assertEqual(lvnTest.valueDict['a'], 2)
        self.assertEqual(lvnTest.valueDict['d'], 3)
        self.assertEqual(len(lvnTest.valueDict), 4)
        self.assertTrue('0Add1' in lvnTest.lvnDict)
        self.assertTrue(isinstance(optimizedTree.body[3].value, ast.Name))
        self.assertEqual(optimizedTree.body[3].value.id, "a")
        source = astor.to_source(optimizedTree)
        print(source)
        # check the ast




