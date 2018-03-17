import unittest
from lvn import lvn
import ast
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



