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

    def assertBlockSsaList(self, real_block_list, expected_block_dict):
        self.assertEqual(len(real_block_list), len(expected_block_dict),
                         "the number of blocks is not the same")
        for key, ssa_string in expected_block_dict.items():
            real_block = real_block_list.get_block_by_name(key)
            self.assertEqual(str(real_block.ssa_code), ssa_string)

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

    def test_rename_given_4_blocks(self):
        as_tree = ast.parse(ms("""\
                    a = 3           # 1st
                    if a > 3:       #  |
                        a = 3       # 2nd
                        b = 3
                    else:           # 3rd
                        z = 4       #  |
                    # expected phi func for 'a' here
                    y = a           # 4th
                    a = 4
                    """)
                            )
        cfg_real = Cfg(as_tree)
        cfg_real.fill_df()
        cfg_real.gather_initial_info()
        cfg_real.ins_phi_function_semi_pruned()
        cfg_real.rename_to_ssa()

        self.assertSsa(cfg_real.block_list[-1].ssa_code.code_list[0],
                       Ssa('a_2', 'a_1', 'Phi', 'a_0'))

    def test_rename_given_custom_4_blocks(self):
        """
               A
            /    \
           B      E
          / \     |
         C  D     |
         \ /      |
          F  <----
        """
        blocks, ast_string = th.build_blocks_arb(block_links={'A': ['B', 'E'], 'B': ['C', 'D'], 'C': ['F'],
                                                              'D': ['F'], 'E': ['G'], 'F': ['G'], 'G': []},
                                                 code={'A': ms("""\
                                                            temp = 0
                                                            """),
                                                       'B': ms("""\
                                                            a = 1 #a_0
                                                            """),
                                                       'C': ms("""\
                                                            a = 22 #a_1
                                                            """),
                                                       'D': ms("""\
                                                            a = 33 #a_2
                                                            """),
                                                       'E': ms("""\
                                                            a = 44 #a_4
                                                            """),
                                                       'F': ms("""\
                                                            a = 55 #a_3
                                                            """),
                                                       'G': ms("""\
                                                            a = 66 #a_5
                                                            """)
                                                       })

        as_tree = ast.parse(ast_string)
        cfg_real = Cfg()
        cfg_real.block_list = blocks
        cfg_real.as_tree = as_tree
        cfg_real.root = cfg_real.block_list[0]
        cfg_real.fill_df()
        cfg_real.gather_initial_info()
        cfg_real.compute_live_out()

        cfg_real.rename_to_ssa()

        self.assertBlockSsaList(cfg_real.block_list,
                                {'A': ms("""\
                                      temp_0 = 0
                                      """),
                                 'B': ms("""\
                                      a_0 = 1
                                      """),
                                 'C': ms("""\
                                      a_1 = 22
                                      """),
                                 'D': ms("""\
                                      a_2 = 33
                                      """),
                                 'E': ms("""\
                                      a_4 = 44
                                      """),
                                 'F': ms("""\
                                      a_3 = 55
                                      """),
                                 'G': ms("""\
                                      a_5 = 66
                                      """)
                                 })


