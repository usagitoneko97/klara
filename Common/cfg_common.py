from collections import deque


def is_blocks_same(block1, block2):
    if block1.start_line == block2.start_line and block1.end_line == block2.end_line and block1.name == block2.name:
        return True
    return False


class GraphWalker:
    def __init__(self, root):
        self.root = root
        self._call_str = ""
        self.closed_block = set()
        self.queue = deque()
        self.blocked_by_call_string = dict()
        self.processed_call_string = set()

    def walk_bfs(self):
        if not self.root:
            return
        self.queue.append(self.root)
        for block in self._walk_bfs():
            yield block

    def _walk_bfs(self):
        while len(self.queue) != 0:
            block = self.queue.popleft()
            if block:
                yield block
                for nxt_blk in block.nxt_block_list:
                    if nxt_blk not in self.queue and nxt_blk not in self.closed_block:
                        self.queue.append(nxt_blk)
                self.closed_block.add(block)

    def walk_dfs(self):
        walk_record = []
        for block in self._walk_dfs(walk_record, self.root):
            yield block

    def _walk_dfs(self, walk_record, basic_block):
        """
        yield nodes from bottom
        :return:
        """
        if basic_block is None:
            return
        walk_record.append(basic_block)
        for next_block in basic_block.nxt_block_list:
            if next_block not in walk_record and next_block is not None:
                for block in self._walk_dfs(walk_record, next_block):
                    yield block
        for block in reversed(self.queue):
            if block not in walk_record and block is not None:
                for block in self._walk_dfs(walk_record, block):
                    yield block
        yield basic_block


def delete_node(root, block_to_delete):
    delete_record = []
    root = _delete_node(delete_record, root, block_to_delete)
    return root


def _delete_node(delete_record, root, block_to_delete):
    if is_blocks_same(root, block_to_delete) or root is None:
        return None

    delete_record.append(root)
    for next_block_num in range(len(root.nxt_block_list)):
        if root.nxt_block_list[next_block_num] not in delete_record:
            root.nxt_block_list[next_block_num] = _delete_node(
                delete_record, root.nxt_block_list[next_block_num], block_to_delete
            )

    # no child left, return yourself
    return root


def find_blocks_involved(root, block_list):
    if root not in block_list:
        block_list.append(root)
    block_involved = []
    for block in GraphWalker(root).walk_bfs():
        block_involved.append(block)
    # to preserve the sequence of block_list
    result = [blk for blk in block_list if blk in block_involved]
    return result
