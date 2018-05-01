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

    def test_initial_info_given_3_simple_stmt_given_if(self):
        as_tree = ast.parse(ms("""\
            a = 3    
            if c < 3:       
                y = a + b         
            """)
                            )

        cfg_real = Cfg(as_tree)
        cfg_real.gather_initial_info()

        expected_ue_var = ({'c'}, {'a', 'b'})
        expected_var_kill = ({'a'}, {'y'})

        self.assertUeVarKill(cfg_real.block_list, expected_ue_var, expected_var_kill)
