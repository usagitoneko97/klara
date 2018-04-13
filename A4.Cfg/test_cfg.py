import unittest
from cfg import Cfg
import ast
import textwrap

ms = textwrap.dedent


class test_cfg(unittest.TestCase):
    def test_cfg_given_no_branch(self):
        as_tree = ast.parse(ms("""\
            a = 3
            a = 4
            """)
        )
        cfg = Cfg(as_tree)
        pass

    def test_cfg_given_call_foo(self):
        as_tree = ast.parse(ms("""\
            a = 3
            a = 4
            foo()
            """)
        )
        cfg = Cfg(as_tree)
        pass

    def test_cfg_given_branch_middle(self):
        as_tree = ast.parse(ms("""\
            a = 3
            foo()
            a = 4
            """)
        )
        cfg = Cfg(as_tree)
        pass

    def test_cfg_given_branch_middle(self):
        as_tree = ast.parse(ms("""\
            foo()
            a = 3
            a = 4
            """)
        )
        cfg = Cfg(as_tree)
        pass