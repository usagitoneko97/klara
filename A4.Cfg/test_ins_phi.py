import unittest
import ast
from common import ms
from cfg import Cfg


class TestInsPhi(unittest.TestCase):
    def assertUeVarKill(self, blocks, expected_ue_var, expected_var_kill):
        for block_num in range(len(blocks)):
            self.assertSetEqual(blocks[block_num].ue_var, expected_ue_var[block_num])
            self.assertSetEqual(blocks[block_num].var_kill, expected_var_kill[block_num])

    def test_initial_info_given_3_simple_stmt_expect_ue_a_vk_a_y_x(self):
        as_tree = ast.parse(ms("""\
            a = 3           
            y = a + b         
            x, y = a, b  
            """)
                            )

        cfg_real = Cfg(as_tree)
        cfg_real.gather_initial_info()

        expected_ue_var = {'b'}
        expected_var_kill = {'a', 'y', 'x'}

        self.assertSetEqual(cfg_real.block_list[0].ue_var, expected_ue_var)
        self.assertSetEqual(cfg_real.block_list[0].var_kill, expected_var_kill)

        expected_globals_var = {'b'}
        self.assertSetEqual(cfg_real.globals_var, expected_globals_var)

        expected_block_set = {'x': [cfg_real.block_list[0]], 'a': [cfg_real.block_list[0]],
                              'y': [cfg_real.block_list[0]]}
        self.assertDictEqual(cfg_real.block_set, expected_block_set)

    def test_initial_info_given_3_simple_stmt_given_if(self):
        as_tree = ast.parse(ms("""\
            a = 3    
            if c < 3:       
                y = a + b
                x, y = a, b         
            """)
                            )

        cfg_real = Cfg(as_tree)
        cfg_real.gather_initial_info()

        expected_ue_var = ({'c'}, {'a', 'b'})
        expected_var_kill = ({'a'}, {'y', 'x'})
        self.assertUeVarKill(cfg_real.block_list, expected_ue_var, expected_var_kill)

        expected_globals_var = {'b', 'a', 'c'}
        self.assertSetEqual(cfg_real.globals_var, expected_globals_var)

        expected_block_set = {'x': [cfg_real.block_list[1]], 'a': [cfg_real.block_list[0]],
                              'y': [cfg_real.block_list[1]]}
        self.assertDictEqual(cfg_real.block_set, expected_block_set)

    # ----------------- test phi function insertion--------------
    def test_insert_phi_function(self):
        as_tree = ast.parse(ms("""\
                    a = 3           # 1st
                    if a > 3:       #  |
                        a = 3       # 2nd
                        b = 3
                    else:           # 3rd
                        z = 4       #  |
                    # expected phi func for 'a' here
                    y = a           # 4th
                    """)
                            )
        cfg_real = Cfg(as_tree)
        cfg_real.fill_df()
        cfg_real.gather_initial_info()
        cfg_real.ins_phi_function_semi_pruned()

        expected_phi_list_for_block_3 = ['a']
        self.assertListEqual(cfg_real.block_list[-1].phi, expected_phi_list_for_block_3)