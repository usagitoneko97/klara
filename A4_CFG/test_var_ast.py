from Common.cfg_common import ms

from cfg import RawBasicBlock, Cfg
import unittest
import ast
from var_ast import VarAst


class TestVarAst(unittest.TestCase):
    def test_VarAst_given_simple_assign(self):
        as_tree = ast.parse(ms("""\
                    y = a + b         
                    """)
                            )
        var_ast = VarAst(as_tree.body[0])

        self.assertListEqual(var_ast.targets_var, ['y'])
        self.assertListEqual(var_ast.values_var, ['a', 'b'])
        self.assertEqual(var_ast.target_op, "Assign")
        self.assertEqual(var_ast.body_op, "Add")

    def test_VarAst_given_if_stmt(self):
        as_tree = ast.parse(ms("""\
                    if a < b:
                        pass     
                    """)
                            )
        var_ast = VarAst(as_tree.body[0])

        self.assertListEqual(var_ast.targets_var, [])
        self.assertListEqual(var_ast.values_var, ['a', 'b'])
        self.assertEqual(var_ast.target_op, "If")
        self.assertEqual(var_ast.body_op, "Lt")

    def test_VarAst_given_while_stmt(self):
        as_tree = ast.parse(ms("""\
                    while a > c:
                        useless_var = 3
                    """)
                            )
        var_ast = VarAst(as_tree.body[0])

        self.assertListEqual(var_ast.targets_var, [])
        self.assertListEqual(var_ast.values_var, ['a', 'c'])
        self.assertEqual(var_ast.target_op, "While")
        self.assertEqual(var_ast.body_op, "Gt")

    def test_VarAst_given_b_const_3(self):
        as_tree = ast.parse(ms("""\
                    z = b + 3
                    """)
                            )
        var_ast = VarAst(as_tree.body[0])

        self.assertListEqual(var_ast.targets_var, ['z'])
        self.assertListEqual(var_ast.values_var, ['b'])
        self.assertEqual(var_ast.target_op, "Assign")
        self.assertEqual(var_ast.body_op, "Add")

        self.assertEqual(var_ast.left_operand, 'b')
        self.assertEqual(var_ast.right_operand, 3)

    def test_VarAst_given_3(self):
        as_tree = ast.parse(ms("""\
                    z = 33
                    """)
                            )
        var_ast = VarAst(as_tree.body[0])

        self.assertListEqual(var_ast.targets_var, ['z'])
        self.assertListEqual(var_ast.values_var, [])
        self.assertEqual(var_ast.target_op, "Assign")
        self.assertEqual(var_ast.body_op, None)

        self.assertEqual(var_ast.left_operand, 33)
        self.assertEqual(var_ast.right_operand, None)


class TestGetVarAst(unittest.TestCase):
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


