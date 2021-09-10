from textwrap import dedent

from klara.core.cfg import Cfg, ParentScopeBlock, RawBasicBlock
from klara.core.tree_rewriter import AstBuilder
from test.helper.base_test import BaseTest


class AssertTrueBasicBlock(Exception):
    pass


class DominatorHelper:
    def assert_df_equal(self, cfg, expected_df_dict):
        assert len(cfg.block_list) == len(expected_df_dict), "the number of blocks is not the same"
        for key, value_list in expected_df_dict.items():
            real_block = cfg.block_list.get_block_by_name(key)
            assert len(real_block.df) == len(value_list), "the number of DF is not the same"
            for real_df_num in range(len(real_block.df)):
                assert real_block.df[real_df_num].name == value_list[real_df_num]

    def assert_dominator_equal(self, cfg_real, expected_dominator_dict):
        assert len(cfg_real.block_list) == len(expected_dominator_dict)

        for key, value_list in expected_dominator_dict.items():
            real_block = cfg_real.block_list.get_block_by_name(key)
            assert len(real_block.rev_dom_list) == len(value_list), "the number of dominated list is not the same"
            real_name_sets = {real.name for real in real_block.rev_dom_list}
            assert real_name_sets == value_list

    def assert_rev_idom_equal(self, cfg_real, expected_idom):
        assert len(cfg_real.block_list) == len(expected_idom)
        for key, value in expected_idom.items():
            real_block = cfg_real.block_list.get_block_by_name(key)
            if value is not None:
                assert real_block.rev_idom.name == value
            else:
                assert real_block.rev_idom is None

    def assert_idom_equal(self, cfg_real, expected_idom):
        for key, expected_values in expected_idom.items():
            real_block = cfg_real.block_list.get_block_by_name(key)
            real_values_str = [v.name for v in real_block.idom]
            assert expected_values == real_values_str


class TestDominator(BaseTest, DominatorHelper):
    # ----------------------- fill dominate test----------------
    def test_fill_dominate_given_if_else(self):
        r"""
          Note: '|' with no arrows means pointing down

           A                      Expected Dominator
         /   \                   A: [B, C, D]
        B     C      ------>     B: []
         \   /                   C: []
           D                     D: []
        """
        blocks = self.build_arbitrary_blocks(
            block_links={"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []},
            block_type={"A": ParentScopeBlock, "B": RawBasicBlock, "C": RawBasicBlock, "D": RawBasicBlock},
        )
        cfg_real = Cfg()
        cfg_real.root = blocks[0]
        cfg_real.root.blocks = blocks
        cfg_real.block_list = blocks

        cfg_real.root.fill_dominates()
        cfg_real.root.fill_idom()
        expected_rev_dominator = {"A": {"A"}, "B": {"A", "B"}, "C": {"A", "C"}, "D": {"A", "D"}}
        expected_idom = {"A": None, "B": "A", "C": "A", "D": "A"}
        self.assert_dominator_equal(cfg_real, expected_rev_dominator)
        self.assert_rev_idom_equal(cfg_real, expected_idom)

    def test_fill_dominate_given_while(self):
        r"""
        Note: '|' with no arrows means pointing down

                A
                |
                B     <-----
               / \         |                            A': ['B', 'C', 'D', 'E', 'F'],
              C   |        |                            B': ['C', 'D', 'E', 'F'],
             / |  |        |    Expected dominator      C': ['D', 'E'],
            D  |  |        |        ---->               D': [],
            |  /  |        |                            E': [],
            E     |        |                            F': []}
            \    /         |
              F   ----------
        """
        blocks = self.build_arbitrary_blocks(
            block_links={"A": ["B"], "B": ["C", "F"], "C": ["D", "E"], "D": ["E"], "E": ["F"], "F": ["B"]},
            block_type={
                "A": ParentScopeBlock,
                "B": RawBasicBlock,
                "C": RawBasicBlock,
                "D": RawBasicBlock,
                "E": RawBasicBlock,
                "F": RawBasicBlock,
            },
        )
        cfg_real = Cfg()
        cfg_real.block_list = blocks
        cfg_real.root = blocks[0]
        cfg_real.root.blocks = blocks

        cfg_real.root.fill_dominates()
        cfg_real.root.fill_idom()

        expected_rev_dominator = {
            "A": {"A"},
            "B": {"A", "B"},
            "C": {"A", "B", "C"},
            "D": {"A", "B", "C", "D"},
            "E": {"A", "B", "C", "E"},
            "F": {"A", "B", "F"},
        }

        expected_idom = {"A": None, "B": "A", "C": "B", "D": "C", "E": "C", "F": "B"}

        self.assert_dominator_equal(cfg_real, expected_rev_dominator)
        self.assert_rev_idom_equal(cfg_real, expected_idom)

    # ------------------ dominator tree test----------------------------
    def test_dominator_tree_given_complex_block(self):
        r"""
                Note: '|' with no arrows means pointing down

                 A                                        A
                 |                                        |
                 B   <------|                             B
              /    \        |     Dominator Tree      /   |   \
             C      F       |       ------->         C    D    F
             |    /  \      |                             |   / | \
             |    G   I     |                             E  G  H  I
             |    \   /     |
             |      H       |
              \    /        |
                D-----------|
                |
                E
        """
        blocks = self.build_arbitrary_blocks(
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
            block_type={
                "A": ParentScopeBlock,
                "B": RawBasicBlock,
                "C": RawBasicBlock,
                "D": RawBasicBlock,
                "E": RawBasicBlock,
                "F": RawBasicBlock,
                "G": RawBasicBlock,
                "H": RawBasicBlock,
                "I": RawBasicBlock,
            },
        )

        cfg_real = Cfg()
        cfg_real.block_list = blocks
        cfg_real.root = blocks[0]
        cfg_real.root.blocks = blocks
        cfg_real.root.fill_dominates()
        cfg_real.root.fill_idom()

        expected_idom = {
            "A": ["B"],
            "B": ["C", "D", "F"],
            "C": [],
            "D": ["E"],
            "E": [],
            "F": ["G", "H", "I"],
            "G": [],
            "H": [],
            "I": [],
        }
        self.assert_idom_equal(cfg_real, expected_idom)

    def test_dominator_tree_given_13_blocks(self):
        r"""
                Note: '|' with no arrows means pointing down

                +---------> R
                |           |
                |     +-----+------------+
                |     |     |            |
                |     A <-- B            C---------+
                |     |    / \           |         |
                |     D --+   E <-+      |         G
                |     |       |   |      F        / \
                |     L       |   |      |       |  J
                |     |       |   |       \      |  |
                |     +------ H --+         I ---+--+
                |             |             |
                |             +---------+   |
                |                       |   |
                +---------------------- K --+
        """
        blocks = self.build_arbitrary_blocks(
            block_links={
                "A": ["B", "C", "H"],
                "B": ["D"],
                "C": ["B", "D", "F"],
                "D": ["E"],
                "E": ["G"],
                "F": ["G"],
                "G": ["F", "M"],
                "H": ["I", "J"],
                "I": ["L"],
                "J": ["K", "L"],
                "K": ["L"],
                "L": ["M"],
                "M": ["A", "L"],
                "N": ["A"],
            },
            block_type={
                "A": RawBasicBlock,
                "B": RawBasicBlock,
                "C": RawBasicBlock,
                "D": RawBasicBlock,
                "E": RawBasicBlock,
                "F": RawBasicBlock,
                "G": RawBasicBlock,
                "H": RawBasicBlock,
                "I": RawBasicBlock,
                "J": RawBasicBlock,
                "K": RawBasicBlock,
                "L": RawBasicBlock,
                "M": RawBasicBlock,
                "N": ParentScopeBlock,
            },
        )
        cfg_real = Cfg()
        cfg_real.block_list = blocks
        cfg_real.root = blocks[-1]
        cfg_real.root.blocks = blocks
        cfg_real.root.fill_dominates()
        cfg_real.root.fill_idom()
        expected_idom = {
            "A": ["B", "C", "D", "F", "G", "H", "L", "M"],
            "B": [],
            "C": [],
            "D": ["E"],
            "E": [],
            "F": [],
            "G": [],
            "H": ["I", "J"],
            "I": [],
            "J": ["K"],
            "K": [],
            "L": [],
            "M": [],
            "N": ["A"],
        }

        self.assert_idom_equal(cfg_real, expected_idom)

    # ---------------------- Dominance Frontier test------------------------
    def test_fill_df_given_6_block_with_loop(self):
        r"""
        Note: '|' with no arrows means pointing down

                A (None)
                |                                       DF(A) : None
                B (B) <-----                            DF(B) : B
               / \         |                            DF(C) : F
            C(F)  |        |                            DF(D) : E
             / |  |        |    Dominance Frontier      DF(E) : F
          D(E) |  |        |        ---->               DF(F) : B
            |  /  |        |
            E(F)  |        |
            \    /         |
             F(B) ----------
        """
        blocks = self.build_arbitrary_blocks(
            block_links={"A": ["B"], "B": ["C", "F"], "C": ["D", "E"], "D": ["E"], "E": ["F"], "F": ["B"]},
            block_type={
                "A": ParentScopeBlock,
                "B": RawBasicBlock,
                "C": RawBasicBlock,
                "D": RawBasicBlock,
                "E": RawBasicBlock,
                "F": RawBasicBlock,
            },
        )

        cfg_real = Cfg()
        cfg_real.block_list = blocks
        cfg_real.root = blocks[0]
        cfg_real.root.blocks = blocks
        cfg_real.fill_df()
        self.assert_df_equal(cfg_real, {"A": [], "B": ["B"], "C": ["F"], "D": ["E"], "E": ["F"], "F": ["B"]})

    def test_fill_df_given_7_blocks(self):
        r"""
        Note: '|' with no arrows means pointing down
             H
             |
             A  <---          DF(A) = A,
            / \    |          DF(B) = G,
           B   E ---          DF(C) = F
          / \  |              DF(D) = F
         C   D |              DF(E) = A, G
          \ /  |              DF(F) = G
           F   |              DF(G) = None
            \  |              DF(H) = None
              G
        """
        blocks = self.build_arbitrary_blocks(
            block_links={
                "H": ["A"],
                "A": ["B", "E"],
                "B": ["C", "D"],
                "C": ["F"],
                "D": ["F"],
                "E": ["G", "A"],
                "F": ["G"],
                "G": [],
            },
            block_type={
                "A": RawBasicBlock,
                "B": RawBasicBlock,
                "C": RawBasicBlock,
                "D": RawBasicBlock,
                "E": RawBasicBlock,
                "F": RawBasicBlock,
                "G": RawBasicBlock,
                "H": ParentScopeBlock,
            },
        )

        cfg_real = Cfg()
        cfg_real.block_list = blocks
        cfg_real.root = blocks[-1]
        cfg_real.root.blocks = blocks
        cfg_real.fill_df()

        self.assert_df_equal(
            cfg_real, {"A": ["A"], "B": ["G"], "C": ["F"], "D": ["F"], "E": ["A", "G"], "F": ["G"], "G": [], "H": []}
        )

    # ----------------- functional tests--------------------------
    # -------------- test build dominator tree----------------

    def test_build_dominator_tree_given_1_lvl(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
            a = 3           # 1st
            if a > 3:       #  |
                a = E       # 2nd
            else:           # 3rd
                z = F       #  |
            y = F           # Eth
            """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.fill_df()

        expected_idom = {
            "L1": ["L3", "L5", "L6"],
            "L5": [],
            "L3": [],
            "L6": ["PhiStub"],
            "Module": ["L1"],
            "PhiStub": [],
        }

        self.assert_idom_equal(cfg_real, expected_idom)

    def test_build_dominator_tree_given_2_lvl(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
             z = 2           # 0th block
             while a < 3:    # 1st block
                 if a < 2:   # 2nd block
                      z = 2  # 3rd block
                 b = 2       # 4th block
             c = 3           # 5th block
            """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.fill_df()
        expected_idom = {
            "L1": ["L2"],
            "L2": ["L3", "L6"],
            "L3": ["L4", "L5"],
            "L4": [],
            "L5": [],
            "L6": ["PhiStub"],
            "Module": ["L1"],
            "PhiStub": [],
        }
        self.assert_idom_equal(cfg_real, expected_idom)


class TestMultipleScope(BaseTest, DominatorHelper):
    def test_1_function_def(self):
        as_tree = AstBuilder().string_build(
            dedent(
                """\
             def foo(x):
                if x < 2:
                    x = 2
                else:
                    x = 1
                z = 1

             f = 5
             z = 5
            """
            )
        )
        cfg_real = Cfg(as_tree)
        cfg_real.fill_df()
        expected_idom = {"foo": ["L2"], "L2": ["L3", "L5", "L6"], "L3": [], "L5": [], "L6": ["PhiStub"], "PhiStub": []}
        self.assert_idom_equal(cfg_real, expected_idom)
        assert cfg_real.block_list[4].df == [cfg_real.block_list[6]]
