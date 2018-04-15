import ast
import common


class BasicBlock:
    BLOCK_IF = 0

    def __init__(self, block_id=0):
        self.ast_list = []
        self.block_id = block_id
        self.nxt_block = []

    def append_node(self, ast_node):
        self.ast_list.append(ast_node)

    def append_block(self, basic_block):
        self.nxt_block.append(basic_block)

    def get_block_type(self):
        if isinstance(self.ast_list[-1], ast.If):
            return self.BLOCK_IF

    def __repr__(self):
        s = ""
        for ast_node in self.ast_list:
            s += ast.dump(ast_node)

        return s


class Cfg:
    def __init__(self, as_tree=None):
        self.block_list = []
        self.cur_block_id = 0
        if as_tree is not None:
            self.get_basic_block(as_tree.body)

    def add_basic_block(self, basic_block):
        if len(basic_block.ast_list) != 0:
            self.block_list.append(basic_block)

    def get_basic_block(self, ast_body):
        """
        yield all simple block in the ast, non recursively
        :param ast_body: ast structure
        :return: yield all simple block
        """
        basic_block = BasicBlock(self.cur_block_id)
        self.cur_block_id += 1
        for ast_node in ast_body:
            basic_block.append_node(ast_node)
            if common.is_if_stmt(ast_node):
                # self.add_basic_block(basic_block)
                yield basic_block
                basic_block = BasicBlock(self.cur_block_id)
                self.cur_block_id += 1
        yield basic_block

        # self.add_basic_block(basic_block)

    def parse(self, ast_body):
        all_tail_list = []
        head = None
        for basic_block in self.get_basic_block(ast_body):

            # link all the tail to the subsequent block
            if all_tail_list.count() == 0:
                head = basic_block
            else:
                self.link_tail_to_cur_block()

            # TODO: linking of basic block when there is no else stmt
            if basic_block.get_block_type() == BasicBlock.BLOCK_IF:
                ast_if_node = basic_block.ast_list[-1]
                head_returned, tail_list = self.parse(ast_if_node.body)

                basic_block.nxt_block.append(head_returned)
                all_tail_list.extend(tail_list)

                head_returned, tail_list = self.parse(ast_if_node.orelse)
                basic_block.nxt_block.append(head_returned)
                all_tail_list.extend(tail_list)

            self.add_basic_block(basic_block)
            return head, all_tail_list







