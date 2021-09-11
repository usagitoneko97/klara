from klara.common.cfg_common import GraphWalker
from test.helper.base_test import BaseTest


class TestBfs:
    def test_bfs_given_4_blk_no_call_string(self):
        r"""
            A
           / \
          B   C
           \ /
            D
        """
        blocks = BaseTest.build_arbitrary_blocks(block_links={"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []})
        gw = GraphWalker(blocks[0])
        blocks_returned = [blk for blk in gw.walk_bfs()]
        assert blocks_returned == [blocks[0], blocks[1], blocks[2], blocks[3]]

    def test_bfs_with_loops(self):
        r"""
          A <---
         / \   |
        B   C --
         \ /
          D
        """
        blocks = BaseTest.build_arbitrary_blocks(block_links={"A": ["B", "C"], "B": ["D"], "C": ["D", "A"], "D": []})
        gw = GraphWalker(blocks[0])
        blocks_returned = [blk for blk in gw.walk_bfs()]
        assert blocks_returned == [blocks[0], blocks[1], blocks[2], blocks[3]]


class TestDfs:
    def test_given_4_simple_blocks(self):
        r"""
             A
           / \
          B   C
           \ /
            D
        """
        blocks = BaseTest.build_arbitrary_blocks(block_links={"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []})
        gw = GraphWalker(blocks[0])
        blocks_returned = [blk for blk in gw.walk_dfs()]
        assert blocks_returned == [blocks[3], blocks[1], blocks[2], blocks[0]]

    def test_given_non_blocking_call_string(self):
        r"""
       -c_1-> A
      |     c_0|
      |        B
      |  c_0 /  c_1\
      -----C       D
        """
        blocks = BaseTest.build_arbitrary_blocks(block_links={"A": ["B"], "B": ["C", "D"], "C": ["A"], "D": []})
        gw = GraphWalker(blocks[0])
        blocks_returned = [blk for blk in gw.walk_dfs()]
        assert blocks_returned == [blocks[2], blocks[3], blocks[1], blocks[0]]
