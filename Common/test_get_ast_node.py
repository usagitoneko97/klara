from unittest import TestCase
import ast
from .cfg_common import get_ast_node
from .common import ms


class TestGet_ast_node(TestCase):
    # ----------------- get ast node test---------------
    def test_get_ast_node_given_2_assign(self):
        as_tree = ast.parse(ms("""\
                       a = 3
                       a = 4
                       """)
                            )

        node = get_ast_node(as_tree, 2)

        self.assertEqual(node, as_tree.body[1])

    def test_get_ast_node_given_if(self):
        as_tree = ast.parse(ms("""\
                       a = 3
                       if a < 3:
                           z = 2
                       a = 4
                       """)
                            )

        node = get_ast_node(as_tree, 3)

        self.assertEqual(node, as_tree.body[1].body[0])

    def test_get_ast_node_given_if_else(self):
        as_tree = ast.parse(ms("""\
                       a = 3
                       if a < 3:
                           z = 2
                       else:
                           y = 2
                       a = 4
                       """)
                            )

        node = get_ast_node(as_tree, 5)

        self.assertEqual(node, as_tree.body[1].orelse[0])

    def test_get_ast_node_given_if_elif_else(self):
        as_tree = ast.parse(ms("""\
                       a = 3
                       if a < 3:
                           z = 2
                       elif z < 2:
                           x = 2
                       else:
                           y = 2
                       a = 4
                       """)
                            )

        node = get_ast_node(as_tree, 5)

        self.assertEqual(node, as_tree.body[1].orelse[0].body[0])

    def test_get_ast_node_given_nested_if(self):
        as_tree = ast.parse(ms("""\
                       a = 3
                       if a < 3:
                           z = 2
                           if y < 2:
                               d = 2
                       a = 4
                       """)
                            )

        node = get_ast_node(as_tree, 5)

        self.assertEqual(node, as_tree.body[1].body[1].body[0])

    def test_get_ast_node_given_function_def(self):
        as_tree = ast.parse(ms("""\
                        y = x + 1
                        def foo(x):
                            y = x + 1
                            if y < 2:
                                z = y
                            return x + 1
                        """))

        node = get_ast_node(as_tree, 4)
        self.assertEqual(node, as_tree.body[1].body[1])

