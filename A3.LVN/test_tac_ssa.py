from tac import Tac, TacSsa, SsaSyntax
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


    def test_ssa_syntax_annotate_and_get_annotate(self):
        a_var = SsaSyntax("a")
        a_var.ssa_annotate(3)

        self.assertEqual(str(a_var), "a#3")

        self.assertEqual(a_var.ssa_get_annotated_num(), 3)

        a_var.ssa_annotate(3)
        self.assertEqual(str(a_var), "a#3")


    def test_ssa_syntax_get_var(self):
        a_var = SsaSyntax("a_var")
        a_var.ssa_annotate(3)

        self.assertEqual(str(a_var), "a_var#3")

        self.assertEqual(a_var.ssa_get_var(), "a_var")


    def test_tac_4_stmt(self):
        as_tree = ast.parse(ms("""\
                            b = 3 + a
                            b = 3 + a
                            b = 3 + a
                            b = 4 + d""")
                            )

        b_stmt = TacSsa()
        b_stmt.append_tac(as_tree.body[0])
        b_stmt.append_tac(as_tree.body[1])
        b_stmt.append_tac(as_tree.body[2])
        b_stmt.append_tac(as_tree.body[3])
        b_stmt.convert_tac_2_ssa()

        self.assert_tac_list(b_stmt.tac_list,
                             target_list=["b#0", "b#1", "b#2", "b#3"],
                             left_oprd_list=['3', '3', '3', '4'],
                             right_oprd_list=["a#0", "a#0", "a#0", "d#0"])

    def test_tac_3_stmt(self):
        as_tree = ast.parse(ms("""\
                            b = c + a
                            a = e + a
                            f = 3 + b""")
                            )

        b_stmt = TacSsa()
        b_stmt.append_tac(as_tree.body[0])
        b_stmt.append_tac(as_tree.body[1])
        b_stmt.append_tac(as_tree.body[2])
        b_stmt.convert_tac_2_ssa()

        self.assert_tac_list(b_stmt.tac_list,
                             target_list=["b#0", "a#1", "f#0"],
                             left_oprd_list=['c#0', 'e#0', '3'],
                             right_oprd_list=["a#0", "a#0", "b#0"])
