from .cfg import Cfg
from A3_LVN.Version2.ssa import SsaCode, Ssa
from Common import cfg_common
import unittest
import ast
import textwrap
import A4_CFG.test_helper as th

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
            self.assertSsaCode(real_block.ssa_code, ssa_string)

    def assertSsaCode(self, real_ssa_code, ssa_list):
        phi_str = ssa_list[0]
        if not isinstance(ssa_list, list):
            for ssa in real_ssa_code.code_list:
                self.assertTrue(str(ssa) in ssa_list, "{} does not contain in {}".format(str(ssa), ssa_list))
        else:
            for real_phi_function in cfg_common.get_all_phi_functions(real_ssa_code):
                if str(real_phi_function) in phi_str:
                    phi_str = phi_str.replace(str(real_phi_function), "", 1)
                else:
                    self.fail(f"phi function {str(real_phi_function)}, does not contain in {ssa_list[0]}")

            self.assertEqual(len("".join(phi_str.split())), 0,
                             f"expected phi function {phi_str} is redundant")

            for ssa in cfg_common.get_all_stmt_without_phi_function(real_ssa_code):
                self.assertTrue(str(ssa) in ssa_list[1], "{} does not contain in {}".format(str(ssa), ssa_list))

    def test_add_ast_node_given_if(self):
        as_tree = ast.parse(ms("""\
                           if a < b:
                               pass
                           """))
        ssa_code = SsaCode()
        ssa_code.add_ast_node_ssa(as_tree.body[0])

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
            ssa_code.add_ast_node_ssa(ast_node)

        ssa_expected_list = [Ssa(None, 'a_0', 'Lt', 'b_0', target_operator='If'),
                             Ssa('a_1', '3', None, None, target_operator='Assign'),
                             Ssa(None, 'a_1', 'Gt', 'b_0', target_operator='While'),
                             Ssa('z_0', '3', None, None, target_operator='Assign')]

        self.assertSsaList(ssa_code.code_list, ssa_expected_list)

    def test_rename_given_input_ast_4_blocks(self):
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

        self.assertBlockSsaList(cfg_real.block_list,
                                {'L1': ms("""\
                                      a_0 = 3
                                      If a_0 > 3
                                      """),
                                 'L3': ms("""\
                                      a_1 = 3
                                      b_0 = 3
                                      """),
                                 'L6': ms("""\
                                      z_0 = 4
                                      """),
                                 'L8': ms("""\
                                      a_2 = a_1 Phi a_0
                                      y_0 = a_2
                                      a_3 = 4
                                      """)
                                 })

    def test_rename_given_repeated_definition(self):
        as_tree = ast.parse(ms("""\
                    a = 3           # 1st
                    if a > 3:       #  |
                        a = 3       # 2nd
                        a = 98
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

        self.assertBlockSsaList(cfg_real.block_list,
                                {'L1': ms("""\
                                      a_0 = 3
                                      If a_0 > 3
                                      """),
                                 'L3': ms("""\
                                      a_1 = 3
                                      a_2 = 98
                                      """),
                                 'L6': ms("""\
                                      z_0 = 4
                                      """),
                                 'L8': [ms("""\
                                      a_3 = a_2 Phi a_0
                                        """),
                                        ms("""\
                                      y_0 = a_3
                                      a_4 = 4
                                         """)]
                                 })

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
        blocks, ast_string = th.build_arbitrary_blocks(block_links={'A': ['B', 'E'], 'B': ['C', 'D'], 'C': ['F'],
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

    def test_renaming_given_loop(self):
        """

                   A
                   |
                   B  <----
                  / \     |
                 C  D     |
                 \ /      |
                  E  -----|
        """
        blocks, ast_string = th.build_arbitrary_blocks(block_links={'A': ['B'], 'B': ['C', 'D'], 'C': ['E'],
                                                              'D': ['E'], 'E': ['B']},
                                                       code={'A': ms("""\
                                                                    j = 1
                                                                    k = 1
                                                                    """),
                                                       'B': ms("""\
                                                                    while I < 29:
                                                                        pass
                                                                    """),
                                                       'C': ms("""\
                                                                    j = j + 1
                                                                    k = k + 1
                                                                    """),
                                                       'D': ms("""\
                                                                    j = j + 2
                                                                    k = k + 2
                                                                    """),
                                                       'E': ms("""\
                                                                    temp = 1
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
        cfg_real.ins_phi_function_pruned()
        cfg_real.rename_to_ssa()

        self.assertBlockSsaList(cfg_real.block_list,
                                {'A': ms("""\
                                              j_0 = 1
                                              k_0 = 1
                                              """),
                                 'B': [ms("""\
                                              k_1 = k_0 Phi k_4
                                              j_1 = j_0 Phi j_4
                                              """),
                                       ms("""\
                                              While I_0 < 29
                                              
                                              """)],
                                 'C': ms("""\
                                              j_2 = j_1 + 1
                                              k_2 = k_1 + 1
                                              """),
                                 'D': ms("""\
                                              j_3 = j_1 + 2
                                              k_3 = k_1 + 2
                                              """),
                                 'E': ms("""\
                                              k_4 = k_2 Phi k_3
                                              j_4 = j_2 Phi j_3
                                              temp_0 = 1
                                              """)
                                 })

    def test_3_blocks_with_loops(self):
        """
            A
            |
            B  <--
            |    |
            | ---
            C
        """
        blocks, ast_string = th.build_arbitrary_blocks(block_links={'A': ['B'], 'B': ['C', 'B'], 'C': []},
                                                       code={'A': ms("""\
                                                                    b = 2
                                                                    c = 1
                                                                    a = 0
                                                                    """),
                                                       'B': ms("""\
                                                                    b = a + 1
                                                                    c = c + b
                                                                    a = b * 2
                                                                    if a < c:
                                                                        pass
                                                                    """),
                                                       'C': ms("""\
                                                                    c = c
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
        cfg_real.ins_phi_function_pruned()
        cfg_real.rename_to_ssa()

        self.assertBlockSsaList(cfg_real.block_list,
                                {'A': ms("""\
                                              b_0 = 2
                                              c_0 = 1
                                              a_0 = 0
                                              """),
                                 'B': [ms("""\
                                            a_1 = a_0 Phi a_2
                                            c_1 = c_0 Phi c_2
                                            """),
                                       ms("""\
                                             b_1 = a_1 + 1
                                             c_2 = c_1 + b_1
                                             a_2 = b_1 * 2
                                             If a_2 < c_2:
                                             """)],
                                 'C': ms("""\
                                              c_3 = c_2
                                              """)
                                 })