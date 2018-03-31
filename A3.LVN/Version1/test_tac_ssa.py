from tac import SsaCode, Ssa
import unittest
import ast
import textwrap

ms = textwrap.dedent


class TestSsaTac(unittest.TestCase):
    def assert_tac(self, tac, target, left_oprd, right_oprd, operator=None):
        self.assertEqual(tac.target, target)
        self.assertEqual(tac.left_oprd, left_oprd)
        self.assertEqual(tac.right_oprd, right_oprd)

        if operator is not None:
            self.assertEqual(tac.operator, operator)

    def assert_tac_list(self, tac_list, target_list, left_oprd_list, right_oprd_list, operator_list=None):
        for i in range(len(tac_list)):
            if operator_list is not None:
                self.assert_tac(tac_list[i], target_list[i], left_oprd_list[i], right_oprd_list[i], operator_list[i])
            else:
                self.assert_tac(tac_list[i], target_list[i], left_oprd_list[i], right_oprd_list[i], None)

    def test_tac_3_stmt(self):
        as_tree = ast.parse(ms("""\
                            a = c + a
                            a = e + a
                            f = 3 + b""")
                            )

        stmt = SsaCode(as_tree)

        self.assertEqual(stmt.code_list[0].version_number, 0)
        self.assertEqual(stmt.code_list[1].version_number, 1)


