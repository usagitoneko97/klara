import unittest
import ast
import textwrap

from tac import SsaCode
from variable_dict import LvnDict
ms = textwrap.dedent


class TestLvnDict(unittest.TestCase):
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

    def test_enumerate_given_a_update(self):
        as_tree = ast.parse(ms("""\
                               a = x + y
                               b = x + y
                               a = 2
                               c = x + y""")
                            )

        ssa_code = SsaCode(as_tree)
        lvn_dict = LvnDict()
        for ssa in ssa_code:
            lvn_dict.enumerate(ssa)

        expected_value_dict = {'a_2': 2, 'x': 0, 'y': 1, 'b': 3, 'a': 4, 'c': 5}
        self.assertDictEqual(lvn_dict.variable_dict, expected_value_dict)

    def test_value_number_to_var_list(self):
        as_tree = ast.parse(ms("""\
                               a = x + y
                               b = x + z
                               a = 2""")
                            )

        ssa_code = SsaCode(as_tree)
        lvn_dict = LvnDict()
        for ssa in ssa_code:
            lvn_dict.append_list(ssa)

        expected_list = ['x', 'y', 'a_2', 'z', 'b', 'a']
        self.assertListEqual(lvn_dict.val_num_var_list, expected_list)

    def test_lvn_code_tuples_to_ssa_code(self):
        """
        a = x + y
        b = 2
        """
        lvn = Lvn()

        lvn.lvn_dict.lvn_code_tuples = [(2, 0, "+", 1, 0),
                                        (3, 2, None, None, 1)]

        lvn.lvn_dict.val_number_list = ['x', 'y', 'a', 'b']

        ssa_code = lvn.lvn_code_to_ssa_code()

        self.assertEqual(ssa_code, ms("""
                                      a = x + y
                                      b = 2
                                      """))





