from common import ms

from cfg import RawBasicBlock, Cfg
import unittest
import ast


class TestVarAst(unittest.TestCase):
    def test_get_ast_stmt_from_block_given_3_simple_ast(self):
        as_tree = ast.parse(ms("""\
            a = 3           
            y = a + b         
            x, y = a, b  
            """)
                            )
        block_1 = RawBasicBlock(1, 3)

        cfg_holder = Cfg()
        cfg_holder.as_tree = as_tree

        tuples_list_real = [(x, y) for x, y in cfg_holder.get_var_ast(block_1)]

        tuples_list_expected = [(['a'], []),
                                (['y'], ['a', 'b']),
                                (['x', 'y'], ['a', 'b'])]

        self.assertListEqual(tuples_list_expected, tuples_list_real)

    def test_get_ast_stmt_from_block_given_if(self):
        as_tree = ast.parse(ms("""\
            a = 3           
            if a < 3:
                x, y = a, b  
            """)
                            )
        block_1 = RawBasicBlock(1, 3)

        cfg_holder = Cfg()
        cfg_holder.as_tree = as_tree

        tuples_list_real = [(x, y) for x, y in cfg_holder.get_var_ast(block_1)]

        tuples_list_expected = [(['a'], []),
                                ([], ['a']),
                                (['x', 'y'], ['a', 'b'])]

        self.assertListEqual(tuples_list_expected, tuples_list_real)

    def test_get_ast_stmt_from_block_given_nested_if(self):
        as_tree = ast.parse(ms("""\
            a = 3           
            if a < 3:
                    if b < 3:
                        x, y = a, b  
            """)
                            )
        block_1 = RawBasicBlock(1, 4)

        cfg_holder = Cfg()
        cfg_holder.as_tree = as_tree

        tuples_list_real = [(x, y) for x, y in cfg_holder.get_var_ast(block_1)]

        tuples_list_expected = [(['a'], []),
                                ([], ['a']),
                                ([], ['b']),
                                (['x', 'y'], ['a', 'b'])]

        self.assertListEqual(tuples_list_expected, tuples_list_real)

    def test_get_ast_stmt_from_block_given_while(self):
        as_tree = ast.parse(ms("""\
            a = 3           
            while a < b:
                    while a > 3:
                        x, y = a, b  
            """)
                            )
        block_1 = RawBasicBlock(1, 4)

        cfg_holder = Cfg()
        cfg_holder.as_tree = as_tree

        tuples_list_real = [(x, y) for x, y in cfg_holder.get_var_ast(block_1)]

        tuples_list_expected = [(['a'], []),
                                ([], ['a', 'b']),
                                ([], ['a']),
                                (['x', 'y'], ['a', 'b'])]

        self.assertListEqual(tuples_list_expected, tuples_list_real)


