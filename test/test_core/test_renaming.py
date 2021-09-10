from textwrap import dedent

from klara.core.cfg import Cfg, ParentScopeBlock
from klara.core.tree_rewriter import AstBuilder
from test.helper.base_test import BaseTest
from test.helper.ssa_th import SsaTestAssertion


class TestRenaming(BaseTest, SsaTestAssertion):
    def test_rename_given_input_ast_4_blocks(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                    a = 3           # 1st
                    if a > 3:       #  |
                        a = 3       # 2nd
                    else:           # 3rd
                        z = 4       #  |
                    # expected phi func for 'a' here
                    y = a           # 4th
                    a = 4
                    """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.fill_df()
        cfg_real.gather_initial_info()
        cfg_real.ins_phi_function_all()
        cfg_real.rename_to_ssa()

        self.assertBlockSsaList(
            cfg_real.block_list,
            {
                "Module": dedent(
                    """\
                                        Module
                                        """
                ),
                "L1": dedent(
                    """\
                                      Assign: (a_0,) = 3
                                      a_0 > 3
                                      """
                ),
                "L3": dedent(
                    """\
                                      Assign: (a_1,) = 3
                                      Assign: (b_0,) = 3
                                      """
                ),
                "L5": dedent(
                    """\
                                      Assign: (z_0,) = 4
                                      """
                ),
                "L7": dedent(
                    """\
                                      Assign: (z_1,) = Phi(z, z_0)
                                      Assign: (a_2,) = Phi(a_1, a_0)
                                      Assign: (y_0,) = a_2
                                      Assign: (a_3,) = 4
                                      """
                ),
            },
        )

    def test_rename_given_repeated_definition(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                    a = 3           # 1st
                    if a > 3:       #  |
                        a = 3       # 2nd
                        a = 98
                    else:           # 3rd
                        z = 4       #  |
                    # expected phi func for 'a' here
                    y = a           # 4th
                    a = 4
                    """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.fill_df()
        cfg_real.gather_initial_info()
        cfg_real.ins_phi_function_all()
        cfg_real.rename_to_ssa()

        self.assertBlockSsaList(
            cfg_real.block_list,
            {
                "Module": dedent(
                    """\
                                      Module
                                            """
                ),
                "L1": dedent(
                    """\
                                      Assign: (a_0,) = 3
                                      a_0 > 3
                                      """
                ),
                "L3": dedent(
                    """\
                                      Assign: (a_1,) = 3
                                      Assign: (a_2,) = 98
                                      """
                ),
                "L6": dedent(
                    """\
                                      Assign: (z_0,) = 4
                                      """
                ),
                "L8": """\
                                      Assign: (z_1,) = Phi(z, z_0)
                                      Assign: (a_3,) = Phi(a_2, a_0)
                                      Assign: (y_0,) = a_3
                                      Assign: (a_4,) = 4
                                      """,
            },
        )

    def test_rename_given_custom_4_blocks(self):
        r"""
               A
            /    \
           B      E
          / \     |
         C  D     |
         \ /      |
          F  <----
        """
        blocks, as_tree = self.build_arbitrary_blocks(
            block_links={"A": ["B", "E"], "B": ["C", "D"], "C": ["F"], "D": ["F"], "E": ["G"], "F": ["G"], "G": []},
            block_type={"A": ParentScopeBlock},
            code={
                "A": dedent(
                    """\
                                                            """
                ),
                "B": dedent(
                    """\
                                                            a = 1 #a_0
                                                            """
                ),
                "C": dedent(
                    """\
                                                            a = 22 #a_1
                                                            """
                ),
                "D": dedent(
                    """\
                                                            a = 33 #a_2
                                                            """
                ),
                "E": dedent(
                    """\
                                                            a = 44 #a_4
                                                            """
                ),
                "F": dedent(
                    """\
                                                            a = 55 #a_3
                                                            """
                ),
                "G": dedent(
                    """\
                                                            a = 66 #a_5
                                                            """
                ),
            },
        )

        cfg_real = Cfg()
        cfg_real.block_list = blocks
        cfg_real.as_tree = as_tree
        cfg_real.root = cfg_real.block_list[0]
        cfg_real.root.ast_node = as_tree
        cfg_real.root.ssa_code.code_list.append(as_tree)
        cfg_real.root.blocks = blocks
        cfg_real.fill_df()
        cfg_real.gather_initial_info()
        cfg_real.compute_live_out()

        cfg_real.rename_to_ssa()

        self.assertBlockSsaList(
            cfg_real.block_list,
            {
                "A": dedent(
                    """\
                                    Module
                                """
                ),
                "B": dedent(
                    """\
                                      Assign: (a_0,) = 1
                                      """
                ),
                "C": dedent(
                    """\
                                      Assign: (a_1,) = 22
                                      """
                ),
                "D": dedent(
                    """\
                                      Assign: (a_2,) = 33
                                      """
                ),
                "E": dedent(
                    """\
                                      Assign: (a_4,) = 44
                                      """
                ),
                "F": dedent(
                    """\
                                      Assign: (a_3,) = 55
                                      """
                ),
                "G": dedent(
                    """\
                                      Assign: (a_5,) = 66
                                      """
                ),
            },
        )

    def test_renaming_given_loop(self):
        r"""

          A
          |
          B  <----
         / \     |
        C  D     |
        \ /      |
         E  -----|
        """
        blocks, as_tree = self.build_arbitrary_blocks(
            block_links={"A": ["B"], "B": ["C", "D"], "C": ["E"], "D": ["E"], "E": ["B"], "F": ["A"]},
            block_type={"F": ParentScopeBlock},
            code={
                "A": dedent(
                    """\
                                                                    j = 1
                                                                    k = 1
                                                                    I = 0
                                                                    """
                ),
                "B": dedent(
                    """\
                                                                    I < 29
                                                                    """
                ),
                "C": dedent(
                    """\
                                                                    j = j + 1
                                                                    k = k + 1
                                                                    """
                ),
                "D": dedent(
                    """\
                                                                    j = j + 2
                                                                    k = k + 2
                                                                    """
                ),
                "E": dedent(
                    """\
                                                                    temp = 1
                                                                    """
                ),
                "F": "",
            },
        )

        cfg_real = Cfg()
        cfg_real.block_list = blocks
        cfg_real.as_tree = as_tree
        cfg_real.root = cfg_real.block_list[-1]
        for blk in cfg_real.block_list[:-1]:
            blk.scope = cfg_real.block_list[-1]
        cfg_real.root.ast_node = as_tree
        cfg_real.root.ssa_code.code_list.append(as_tree)
        cfg_real.root.blocks = blocks
        cfg_real.convert_to_ssa()

        self.assertBlockSsaList(
            cfg_real.block_list,
            {
                "A": dedent(
                    """\
                                              Assign: (j_0,) = 1
                                              Assign: (k_0,) = 1
                                              Assign: (I_0,) = 0
                                              """
                ),
                "B": dedent(
                    """\
                                              Assign: (temp_0,) = Phi(temp, temp_1)
                                              Assign: (k_1,) = Phi(k_0, k_4)
                                              Assign: (j_1,) = Phi(j_0, j_4)
                                              I_0 < 29
                                              """
                ),
                "C": dedent(
                    """\
                                              Assign: (j_2,) = BinOp: j_1 + 1
                                              Assign: (k_2,) = BinOp: k_1 + 1
                                              """
                ),
                "D": dedent(
                    """\
                                              Assign: (j_3,) = BinOp: j_1 + 2
                                              Assign: (k_3,) = BinOp: k_1 + 2
                                              """
                ),
                "E": dedent(
                    """\
                                              Assign: (k_4,) = Phi(k_2, k_3)
                                              Assign: (j_4,) = Phi(j_2, j_3)
                                              Assign: (temp_1,) = 1
                                              """
                ),
                "F": "Module ",
            },
        )

    def test_3_blocks_with_loops(self):
        r"""
        A
        |
        B  <--
        |    |
        | ---
        C
        """
        blocks, as_tree = self.build_arbitrary_blocks(
            block_links={"A": ["B"], "B": ["C", "B"], "C": [], "D": ["A"]},
            block_type={"D": ParentScopeBlock},
            code={
                "A": dedent(
                    """\
                                                                    b = 2
                                                                    c = 1
                                                                    a = 0
                                                                    """
                ),
                "B": dedent(
                    """\
                                                                    b = a + 1
                                                                    c = c + b
                                                                    a = b * 2
                                                                    a < c
                                                                    """
                ),
                "C": dedent(
                    """\
                                                                    c = c
                                                                    """
                ),
                "D": "",
            },
        )

        cfg_real = Cfg()
        cfg_real.block_list = blocks
        cfg_real.as_tree = as_tree
        cfg_real.root = cfg_real.block_list[-1]
        for blk in cfg_real.block_list[:-1]:
            blk.scope = cfg_real.block_list[-1]
        cfg_real.root.ast_node = as_tree
        cfg_real.root.ssa_code.code_list.append(as_tree)
        cfg_real.root.blocks = blocks
        cfg_real.convert_to_ssa()
        self.assertBlockSsaList(
            cfg_real.block_list,
            {
                "A": dedent(
                    """\
                                              Assign: (b_0,) = 2
                                              Assign: (c_0,) = 1
                                              Assign: (a_0,) = 0
                                              """
                ),
                "B": dedent(
                    """\
                                             Assign: (a_1,) = Phi(a_0, a_2)
                                             Assign: (c_1,) = Phi(c_0, c_2)
                                             Assign: (b_1,) = Phi(b_0, b_2)
                                             Assign: (b_2,) = BinOp: a_1 + 1
                                             Assign: (c_2,) = BinOp: c_1 + b_2
                                             Assign: (a_2,) = BinOp: b_2 * 2
                                             a_2 < c_2
                                             """
                ),
                "C": dedent(
                    """\
                                              Assign: (c_3,) = c_2
                                              """
                ),
            },
        )

    def test_renaming_multiple_scope(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                        def foo(x):
                            a = 3
                            return x

                        a = 2
                        foo(a)
                        """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        self.assertBlockSsaList(
            cfg_real.block_list,
            {
                "L2": dedent(
                    """\
                                            Assign: (ret_val_0,) = x_0
                                            Assign: (a_0,) = 3
                                    """
                ),
                "L5": dedent(
                    """\
                                            Assign: (a_0,) = 2
                                            Call: foo_0((a_0,))
                                            """
                ),
            },
        )

    def test_renaming_functiondef_replaced(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                        def foo(x):
                            return x

                        def foo():
                            pass

                        a = 2
                        foo(a)
                        """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        self.assertBlockSsaList(
            cfg_real.block_list,
            {
                "L7": dedent(
                    """\
                                    Assign: (a_0,) = 2
                                    Call: foo_1((a_0,))
                                    """
                )
            },
        )

    def test_renaming_given_3_scopes(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                        class Foo():
                            x = 1
                            def __init__(self):
                                x = 2
                        x = 3
                        f = Foo(2)
                        """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        self.assertBlockSsaList(
            cfg_real.block_list,
            {
                "L2": dedent(
                    """\
                    Assign: (x_0,) = 1
                    Assign: (__init___0,) = Proxy to the object: Function __init__ in scope Class "Foo" in scope Module
                    """
                ),
                "L4": "Assign: (x_0,) = 2",
                "L5": dedent(
                    """\
                    Assign: (x_0,) = 3
                    Assign: (f_0,) = Call: Foo_0((2,))
                    """
                ),
            },
        )

    def test_renaming_args_expression(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                        def foo(x):
                            return x + 1
                        y = 2
                        y = 3
                        z = 4
                        foo(y + 2 / z * 43)
                        """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        self.assertBlockSsaList(
            cfg_real.block_list,
            {
                "L3": dedent(
                    """\
                                    Assign: (y_0,) = 2
                                    Assign: (y_1,) = 3
                                    Assign: (z_0,) = 4
                                    Call: foo_0((BinOp: y_1 + BinOp: BinOp: 2 / z_0 * 43,))
                                    """
                )
            },
        )

    def test_renaming_args_attribute(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                        class Temp:
                            def __init__(self):
                                pass

                        def foo(x):
                            return x + 1

                        y = Temp()
                        y.z = 3
                        foo(y.z)
                        """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        self.assertBlockSsaList(
            cfg_real.block_list,
            {
                "L9": dedent(
                    """\
                                    Assign: (y_0.z_0,) = 3
                                    Call: foo_0((y_0.z_0,))
                                    """
                )
            },
        )

    def test_renaming_globals_var_1_var(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                        def foo(x):
                            x = y
                        """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        self.assertBlockSsaList(
            cfg_real.block_list,
            {
                "L2": dedent(
                    """\
                                    Assign: (x_1,) = y
                                    """
                )
            },
        )

    def test_renaming_globals_var_replaced(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                        def foo(x):
                            z = y
                            y = 2
                            x = y
                        """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        self.assertBlockSsaList(
            cfg_real.block_list,
            {
                "L2": dedent(
                    """\
                                    Assign: (z_0,) = y
                                    Assign: (y_0,) = 2
                                    Assign: (x_1,) = y_0
                                    """
                )
            },
        )

    def test_renaming_nameconstant(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                        if True:
                            x = True
                        else:
                            x = None
                        if False:
                            pass
                        """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        self.assertBlockSsaList(
            cfg_real.block_list,
            {
                "L1": dedent(
                    """\
                                    True
                                    """
                ),
                "L4": "Assign: (x_1,) = None",
                "L5": dedent(
                    """\
                                    Assign: (x_2,) = Phi(x_0, x_1)
                                    False
                                    """
                ),
            },
        )

    def test_renaming_list_simple(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                    a = 2
                    a = 1 + 2 - 3
                    l = [1, 2, a, "s"]
                    s = l[a + 1:a + 3]
                        """
            )
        )
        str(as_tree.body[-1].value.slice)
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        self.assertBlockSsaList(
            cfg_real.block_list,
            {
                "L1": dedent(
                    """\
                                    Assign: (a_0,) = 2
                                    Assign: (a_1,) = BinOp: BinOp: 1 + 2 - 3
                                    Assign: (l_0,) = [1, 2, a_1, 's']
                                    Assign: (s_0,) = l_0[BinOp: a_1 + 1:BinOp: a_1 + 3:'']
                                    """
                )
            },
        )

    def test_renaming_list_phi_values(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                    if True:
                        l = [1, 2, 3, "s"]
                    else:
                        l = [4, 5, 6, True]
                    s = l[1:]
                        """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        self.assertBlockSsaList(
            cfg_real.block_list,
            {
                "L5": dedent(
                    """\
                                    Assign: (l_2,) = Phi(l_0, l_1)
                                    Assign: (s_0,) = l_2[1:'':'']
                                    """
                )
            },
        )

    def test_renaming_subscript_assignment(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                    l = [1, 2, 3]
                    l[2] = 4
                    l[1:] = [2, 3]
                    l[1] = 5
                    l[2] = 10
                        """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        self.assertBlockSsaList(
            cfg_real.block_list,
            {
                "L1": dedent(
                    """\
                                    Assign: (l_0,) = [1, 2, 3]
                                    Assign: (l_0[2]_0,) = 4
                                    Assign: (l_0[1:'':'']_0,) = [2, 3]
                                    Assign: (l_0[1]_0,) = 5
                                    Assign: (l_0[2]_1,) = 10
                                    """
                )
            },
        )

    def test_renaming_tuple_packing_unpacking(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                    a = b = 1
                    (a, b) = (1, 1)
                    """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        self.assertBlockSsaList(
            cfg_real.block_list,
            {
                "L1": dedent(
                    """\
                                    Assign: (a_0, b_0) = 1
                                    Assign: ((a_1, b_1),) = (1, 1)
                                    """
                )
            },
        )

    def test_renaming_starred_var(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                    a = b = 1
                    a, *b = (1, 1)
                    """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        self.assertBlockSsaList(
            cfg_real.block_list,
            {
                "L1": dedent(
                    """\
                                    Assign: (a_0, b_0) = 1
                                    Assign: ((a_1, *b_1),) = (1, 1)
                                    """
                )
            },
        )

    def test_renaming_for(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                    for i in iter():
                        z = i
                    z = i
                    """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        self.assertBlockSsaList(
            cfg_real.block_list,
            {
                "L1": dedent(
                    """\
                                    Assign: (i_0,) = Phi(i, i_1)
                                    Assign: (z_0,) = Phi(z, z_1)
                                    Assign: (i_1,) = ForIter: Call: iter(())
                                    """
                ),
                "L2": "Assign: (z_1,) = i_1",
                "L3": "Assign: (z_2,) = i_1",
            },
        )

    def test_renaming_for_while(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                    bi = 1
                    b = 2
                    cycle = False
                    first = True
                    while cycle or first:
                        while b is None or (bi < b and b > o):
                            for c in [c] * repeat:
                                yield c
                    """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        self.assertBlockSsaList(
            cfg_real.block_list,
            {
                "L6": dedent(
                    """\
                                    Assign: (c_1,) = Phi(c_0, c_3)
                                    b_0 is None or bi_0 < b_0 and b_0 > o
                                    """
                )
            },
        )

    def test_renaming_import_as(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                    import abc
                    from abc import s
                    import abc as abc
                    abc.s = 1
                    """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        self.assertBlockSsaList(
            cfg_real.block_list,
            {
                "L1": dedent(
                    """\
                                    import (abc_0 ,)
                                    from abc import (s_0 ,)
                                    import (abc as abc_1,)
                                    Assign: (abc_1.s_0,) = 1
                                    """
                )
            },
        )

    def test_renaming_str_format(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                    v = 1
                    s = "some{}".format(v)
                    """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()

    def test_renaming_for_var(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                    for line in something:
                        if x:
                            line = "s".join('y')
                        else:
                            line = "z".join('y')
                        line.strip()
                    """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()

    def test_renaming_phi_func_elif(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
            class C:
                def Top(self):
                    # IO: have 55 io in each  local block
                    self.max_rlc = 55
                    self.nlc = (self.number -1)/self.max_rlc + 1

                    self.pp_key_num = self.pp_key_num + self.re
                    if(self.pp_en):
                        self.nlc = 3
                        self.pp_key_num = self.pp_key_num + self.re

                    self.number = self.number + self.nlc * self.re

                    self.number_2lc = 0

                    res = "d"
                    if self.nlc == 1:
                        res = "a"

                    elif self.nlc == 2:
                        self.number_2lc = self.number - self.number_1lc

                    elif self.nlc == 3:
                        self.number_2lc = self.nio_2lc * 2
                    z = self.number_2lc
                    """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.convert_to_ssa()
        self.assertBlockSsaList(
            cfg_real.block_list,
            {
                "L25": dedent(
                    """\
                    Assign: (res_2,) = Phi(res_1, res_0)
                    Assign: (self_0.number_2lc_3,) = Phi(self_0.number_2lc_0, self_0.number_2lc_1, self_0.number_2lc_2)
                    Assign: (z_0,) = self_0.number_2lc_3"""
                )
            },
        )
