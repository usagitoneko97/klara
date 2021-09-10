import unittest
from textwrap import dedent

from klara.core.cfg import Cfg, ParentScopeBlock
from klara.core.tree_rewriter import AstBuilder

from ..helper.base_test import BaseTest


class TestInitialInfoLiveout(BaseTest):
    def assert_uevar_varkill(self, blocks, expected_ue_var, expected_var_kill):
        for block_num in range(len(blocks)):
            assert blocks[block_num].ue_var == expected_ue_var[block_num]
            assert blocks[block_num].var_kill == expected_var_kill[block_num]

    def assertLiveOutEqual(self, block_list, expected_live_out_dict):
        for block_name, expected_live_out_set in expected_live_out_dict.items():
            real_block = block_list.get_block_by_name(block_name)
            assert real_block.live_out == expected_live_out_set

    # -------------------- test compute initial info------------------------------
    def test_initial_info_given_3_simple_stmt_expect_ue_a_vk_a_y_x(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
            a = 3
            y = a + b
            x = a
            y = b
            """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.gather_initial_info()

        expected_ue_var = {"b"}
        expected_var_kill = {"a", "y", "x"}

        assert cfg_real.block_list[1].ue_var == expected_ue_var
        assert cfg_real.block_list[1].var_kill == expected_var_kill

        expected_globals_var = {"b"}
        assert cfg_real.globals_var == expected_globals_var

        real_block_set = {str(k): v for k, v in cfg_real.block_set.items()}
        expected_block_set = {"x": cfg_real.block_list[1], "a": cfg_real.block_list[1], "y": cfg_real.block_list[1]}
        assert real_block_set == expected_block_set

    def test_initial_info_given_3_simple_stmt_given_if(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
            a = 3
            if c < 3:
                y = a + b
                x = a
                y = b
                a.b = c
            """
            )
        )

        cfg_real = Cfg(as_tree)
        cfg_real.gather_initial_info()

        expected_ue_var = (set(), {"c"}, {"a", "b", "c"}, set())
        expected_var_kill = (set(), {"a"}, {"y", "x", "a.b"}, set())
        self.assert_uevar_varkill(cfg_real.block_list, expected_ue_var, expected_var_kill)

        expected_globals_var = {"b", "a", "c"}
        assert cfg_real.globals_var == expected_globals_var

        real_block_set = {str(k): v for k, v in cfg_real.block_set.items()}
        expected_block_set = {
            "x": cfg_real.block_list[2],
            "a": cfg_real.block_list[1],
            "y": cfg_real.block_list[2],
            "a.b": cfg_real.block_list[2],
        }
        assert real_block_set == expected_block_set

    def test_with_simple_attr(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
            a.b = c.d
            """
            )
        )

        cfg_real = Cfg(as_tree)
        cfg_real.gather_initial_info()
        expected_ue_var = {"a", "c", "c.d"}
        expected_var_kill = {"a.b"}
        assert cfg_real.block_list[1].ue_var == expected_ue_var
        assert cfg_real.block_list[1].var_kill == expected_var_kill

    def test_uevar_varkill_with_attr(self):
        """`a` and `c.d` is assigned before. It shouldn't be in UEVAR set"""
        as_tree = AstBuilder().string_build(
            dedent(
                """\
            a = 2
            c.d = 2
            a.b = c.d
            """
            )
        )

        cfg_real = Cfg(as_tree)
        cfg_real.gather_initial_info()
        expected_ue_var = {"c"}
        expected_var_kill = {"a", "a.b", "c.d"}
        assert cfg_real.block_list[1].ue_var == expected_ue_var
        assert cfg_real.block_list[1].var_kill == expected_var_kill

    # -------------------- test compute liveout------------------------------
    def test_compute_liveout_given_5_blocks(self):
        blocks, as_tree = self.build_arbitrary_blocks(
            block_links={"A": ["B"], "B": ["C", "D"], "C": ["D"], "D": ["E", "B"], "E": []},
            code={
                "A": dedent(
                    """\
                                                                    i = 1
                                                                    """
                ),
                "B": dedent(
                    """\
                                                                    if i < 0:
                                                                        pass
                                                                    """
                ),
                "C": dedent(
                    """\
                                                                    s = 0
                                                                    """
                ),
                "D": dedent(
                    """\
                                                                    s = s + i
                                                                    i = i + 1
                                                                    if i < 0:
                                                                        pass
                                                                    """
                ),
                "E": dedent(
                    """\
                                                                    if s < 3:
                                                                        pass
                                                                    """
                ),
            },
        )
        cfg_real = Cfg()
        cfg_real.block_list = blocks
        cfg_real.as_tree = as_tree
        cfg_real.root = cfg_real.block_list[0]
        cfg_real.gather_initial_info()
        cfg_real.compute_live_out()
        expected_live_out = {"A": {"s", "i"}, "B": {"s", "i"}, "C": {"s", "i"}, "D": {"s", "i"}, "E": set()}
        self.assertLiveOutEqual(cfg_real.block_list, expected_live_out)

    def test_compute_liveout_with_attr(self):
        blocks, as_tree = self.build_arbitrary_blocks(
            block_links={"A": ["B"], "B": []},
            code={
                "A": dedent(
                    """\
                                                                    a = 4
                                                                    a.b = 2
                                                                    """
                ),
                "B": dedent(
                    """\
                                                                    c = a.b
                                                                    """
                ),
            },
        )
        cfg_real = Cfg()
        cfg_real.block_list = blocks
        cfg_real.as_tree = as_tree
        cfg_real.root = cfg_real.block_list[0]
        cfg_real.gather_initial_info()
        cfg_real.compute_live_out()
        expected_live_out = {"A": {"a", "a.b"}, "B": set()}
        self.assertLiveOutEqual(cfg_real.block_list, expected_live_out)

    # ------------------ test recompute_liveout----------------------------
    def test_recompute_liveout(self):
        # Given: UEVAR(B) = 'c'
        # Expect: LIVEOUT(A) = 'c'
        blocks = self.build_arbitrary_blocks(block_links={"A": ["B"], "B": []})
        blocks[1].ue_var.add("c")
        assert blocks[0].recompute_liveout() is True
        assert blocks[0].live_out == {"c"}

        # Given: UEVAR(B) = 'c',
        #        LIVEOUT(B) = 'd'
        #        VARKILL(B) = None
        # Expect: LIVEOUT(A) = 'c, 'd'

        blocks = self.build_arbitrary_blocks(block_links={"A": ["B"], "B": []})
        blocks[1].ue_var.add("c")
        blocks[1].live_out.add("d")
        assert blocks[0].recompute_liveout() is True
        assert blocks[0].live_out == {"c", "d"}

        # Given: UEVAR(B) = 'c',
        #        LIVEOUT(B) = 'd'
        #        VARKILL(B) = 'd'
        # Expect: LIVEOUT(A) = 'c'

        blocks = self.build_arbitrary_blocks(block_links={"A": ["B"], "B": []})
        blocks[1].ue_var.add("c")
        blocks[1].live_out.add("d")
        blocks[1].var_kill.add("d")
        assert blocks[0].recompute_liveout() is True
        assert blocks[0].live_out == {"c"}

        # Given: LIVEOUT(A) = 'c'
        #        UEVAR(B) = 'c',
        #        LIVEOUT(B) = 'd'
        #        VARKILL(B) = 'd'
        # Expect: LIVEOUT(A) = 'c' (no changed)

        blocks = self.build_arbitrary_blocks(block_links={"A": ["B"], "B": []})
        blocks[0].live_out.add("c")
        blocks[1].ue_var.add("c")
        blocks[1].live_out.add("d")
        blocks[1].var_kill.add("d")
        assert blocks[0].recompute_liveout() is False
        assert blocks[0].live_out == {"c"}


class TestInsPhi(BaseTest):
    def assertPhiListEqual(self, block_list, expected_phi_list_dict):
        for block_name, expected_phi_list in expected_phi_list_dict.items():
            real_block = block_list.get_block_by_name(block_name)
            assert real_block._phi_repr == expected_phi_list

    # ------------------- test phi function insertion-----------------------
    @unittest.skip("pruned/semipruned phi function is deprecated")
    def test_insert_phi_function_semi_pruned(self):
        r"""
           Note: '|' with no arrows means pointing down

            A
            |
            B   <------|
         /    \        |
        C      F       |
        |    /  \      |
        |    G   I     |
        |    \   /     |
        |      H       |
         \    /        |
           D-----------|
           |
           E
        """
        blocks, as_tree = self.build_arbitrary_blocks(
            block_links={
                "A": ["B"],
                "B": ["C", "F"],
                "C": ["D"],
                "D": ["E", "B"],
                "E": [],
                "F": ["G", "I"],
                "G": ["H"],
                "H": ["D"],
                "I": ["H"],
            },
            code={
                "A": dedent(
                    """\
                                                            i = 1
                                                            """
                ),
                "B": dedent(
                    """\
                                                            a = temp_0
                                                            c = temp_1
                                                            """
                ),
                "C": dedent(
                    """\
                                                            b = temp_2
                                                            c = temp_3
                                                            d = temp_4
                                                            """
                ),
                "D": dedent(
                    """\
                                                            y = a + b
                                                            z = c + d
                                                            i = i + 1
                                                            if i < 100:
                                                                pass
                                                            """
                ),
                "E": "return\n",
                "F": dedent(
                    """\
                                                            a = temp_5
                                                            d = temp_6
                                                            if a < d:
                                                                pass
                                                            """
                ),
                "G": dedent(
                    """\
                                                            d = temp
                                                            """
                ),
                "H": dedent(
                    """\
                                                            b = temp
                                                            """
                ),
                "I": dedent(
                    """\
                                                            c = temp
                                                            """
                ),
            },
            block_type={"A": ParentScopeBlock},
        )
        cfg_real = Cfg()
        cfg_real.block_list = blocks
        cfg_real.as_tree = as_tree
        cfg_real.root = cfg_real.block_list[0]
        cfg_real.root.blocks = blocks
        cfg_real.fill_df()
        cfg_real.gather_initial_info()
        cfg_real.ins_phi_function_semi_pruned()

        expected_phi_list = {
            "A": set(),
            "B": {"a", "b", "c", "d", "i"},
            "C": set(),
            "D": {"a", "b", "c", "d"},
            "E": set(),
            "F": set(),
            "G": set(),
            "H": {"c", "d"},
            "I": set(),
        }

        self.assertPhiListEqual(cfg_real.block_list, expected_phi_list)

    @unittest.skip("pruned/semipruned phi function is deprecated")
    def test_insert_phi_function_pruned(self):
        r"""
           Note: '|' with no arrows means pointing down

            A
            |
            B   <------|
         /    \        |
        C      F       |
        |    /  \      |
        |    G   I     |
        |    \   /     |
        |      H       |
         \    /        |
           D-----------|
           |
           E
        """
        blocks, as_tree = self.build_arbitrary_blocks(
            block_links={
                "A": ["B"],
                "B": ["C", "F"],
                "C": ["D"],
                "D": ["E", "B"],
                "E": [],
                "F": ["G", "I"],
                "G": ["H"],
                "H": ["D"],
                "I": ["H"],
            },
            code={
                "A": dedent(
                    """\
                                                            i = 1
                                                            """
                ),
                "B": dedent(
                    """\
                                                            a = temp_0
                                                            c = temp_1
                                                            if a < c:
                                                                pass
                                                            """
                ),
                "C": dedent(
                    """\
                                                            b = temp_2
                                                            c = temp_3
                                                            d = temp_4
                                                            """
                ),
                "D": dedent(
                    """\
                                                            y = a + b
                                                            z = c + d
                                                            i = i + 1
                                                            if i < 100:
                                                                pass
                                                            """
                ),
                "E": "return\n",
                "F": dedent(
                    """\
                                                            a = temp_5
                                                            d = temp_6
                                                            if a < d:
                                                                pass
                                                            """
                ),
                "G": dedent(
                    """\
                                                            d = temp
                                                            """
                ),
                "H": dedent(
                    """\
                                                            b = temp
                                                            """
                ),
                "I": dedent(
                    """\
                                                            c = temp
                                                            """
                ),
            },
            block_type={"A": ParentScopeBlock},
        )
        cfg_real = Cfg()
        cfg_real.block_list = blocks
        cfg_real.as_tree = as_tree
        cfg_real.root = cfg_real.block_list[0]
        cfg_real.root.blocks = blocks
        cfg_real.fill_df()
        cfg_real.gather_initial_info()
        cfg_real.compute_live_out()
        cfg_real.ins_phi_function_all()
        expected_phi_list = {
            "A": set(),
            "B": {"i"},
            "C": set(),
            "D": {"a", "b", "c", "d"},
            "E": set(),
            "F": set(),
            "G": set(),
            "H": {"c", "d"},
            "I": set(),
        }
        self.assertPhiListEqual(cfg_real.block_list, expected_phi_list)

    def test_insert_phi_function_pruned_4_blocks(self):
        blocks, as_tree = self.build_arbitrary_blocks(
            block_links={"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []},
            code={
                "A": dedent(
                    """\
                                                            pass
                                                            """
                ),
                "B": dedent(
                    """\
                                                            var = 3
                                                            """
                ),
                "C": dedent(
                    """\
                                                            pass
                                                            """
                ),
                "D": dedent(
                    """\
                                                            if var < 3:
                                                                pass
                                                            """
                ),
            },
            block_type={"A": ParentScopeBlock},
        )
        cfg_real = Cfg()
        cfg_real.block_list = blocks
        cfg_real.as_tree = as_tree
        cfg_real.root = cfg_real.block_list[0]
        cfg_real.root.blocks = blocks
        cfg_real.fill_df()
        cfg_real.gather_initial_info()
        cfg_real.compute_live_out()
        cfg_real.ins_phi_function_all()
        expected_phi_list = {"A": set(), "B": set(), "C": set(), "D": {"var"}}
        self.assertPhiListEqual(cfg_real.block_list, expected_phi_list)

    # ----------------- functional test phi function insertion--------------
    def test_insert_phi_function_if_else(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
                    a = 3           # 1st
                    if a > 3:       #  |
                        a = 3       # 2nd
                        b = 3
                    else:           # 3rd
                        z = 4       #  |
                    # expected phi func for 'a' here
                    y = a           # 4th
                    """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.fill_df()
        cfg_real.gather_initial_info()
        cfg_real.ins_phi_function_all()
        assert cfg_real.block_list[-2]._phi_repr == {"a", "b", "z"}
        cfg_real.rename_to_ssa()
        assert "Phi(a_1, a_0)" in str(cfg_real.block_list[-2].ssa_code.code_list)
