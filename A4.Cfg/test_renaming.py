from cfg import Cfg, build_blocks, DominatorTree
from ssa import SsaCode, Ssa
import cfg_common
import unittest
import ast
import textwrap
import test_helper as th

ms = textwrap.dedent


class TestRenaming(unittest.TestCase):
    def assertSsaVariable(self, ssa_var_real, ssa_var_expected):
        if ssa_var_expected is None:
            self.assertIsNone(ssa_var_real)
        else:
            self.assertEqual(str(ssa_var_real), ssa_var_expected)

    def assertSsa(self, ssa_real, ssa_expected):
        self.assertSsaVariable(ssa_real.target, ssa_expected.target)
        self.assertSsaVariable(ssa_real.left_oprd, ssa_expected.left_oprd)
        self.assertSsaVariable(ssa_real.right_oprd, ssa_expected.right_oprd)
        self.assertEqual(ssa_real.operator, ssa_expected.operator)
        self.assertEqual(ssa_real.target_operator, ssa_expected.target_operator)

    def assertSsaList(self, ssa_real_list, ssa_expected_list):
        self.assertEqual(len(ssa_real_list), len(ssa_expected_list), "the number of ssa statements is not the same")
        for ssa_num in range(len(ssa_real_list)):
            self.assertSsa(ssa_real_list[ssa_num], ssa_expected_list[ssa_num])

    def test_add_ast_node_given_if(self):
        as_tree = ast.parse(ms("""\
                           if a < b:
                               pass
                           """))
        ssa_code = SsaCode()
        ssa_code.add_ast_node(as_tree.body[0])

        ssa_expected = Ssa(None, 'a_0', 'Lt', 'b_0', target_operator='If')
        self.assertSsa(ssa_code.code_list[0], ssa_expected)

    def test_add_ast_node_given_while(self):
        as_tree = ast.parse(ms("""\
                            if a < b:
                                a = 3
                            while a > b:
                                z = 3
                            """))
        ssa_code = SsaCode()

        for i in range(1, 5):
            ast_node = cfg_common.get_ast_node(as_tree, i)
            ssa_code.add_ast_node(ast_node)

        ssa_expected_list = [Ssa(None, 'a_0', 'Lt', 'b_0', target_operator='If'),
                             Ssa('a_1', '3', None, None, target_operator='Assign'),
                             Ssa(None, 'a_1', 'Gt', 'b_0', target_operator='While'),
                             Ssa('z_0', '3', None, None, target_operator='Assign')]

        self.assertSsaList(ssa_code.code_list, ssa_expected_list)



