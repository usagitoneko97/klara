import ast
import common


class BasicBlock:
    BLOCK_IF = 0
    IS_TRUE_BLOCK = 0
    IS_FALSE_BLOCK = 1

    def __init__(self, block_id=0, ast_list=None):
        self.ast_list = []
        self.block_id = block_id
        self.nxt_block = []
        if ast_list is not None:
            self.ast_list.extend(ast_list)

    def append_node(self, ast_node):
        self.ast_list.append(ast_node)

    def get_block_type(self):
        if isinstance(self.ast_list[-1], ast.If):
            return self.BLOCK_IF

    def __repr__(self):
        s = ""
        for ast_node in self.ast_list:
            s += ast.dump(ast_node)

        return s


class Cfg:
    def __init__(self, as_tree=None, *basic_block_args):
        self.block_list = []
        self.cur_block_id = 0
        if as_tree is not None:
            self.parse(as_tree.body)

        if len(basic_block_args) != 0:
            for basic_block in basic_block_args:
                self.add_basic_block(basic_block)

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
            if len(all_tail_list) == 0:
                head = basic_block
            else:
                pass
                # self.link_tail_to_cur_block()

            # TODO: linking of basic block when there is no else stmt
            self.add_basic_block(basic_block)
            if basic_block.get_block_type() == BasicBlock.BLOCK_IF:
                ast_if_node = basic_block.ast_list[-1]
                head_returned, tail_list = self.parse(ast_if_node.body)

                basic_block.nxt_block.insert(BasicBlock.IS_TRUE_BLOCK, head_returned)
                all_tail_list.extend(tail_list)

                head_returned, tail_list = self.parse(ast_if_node.orelse)
                basic_block.nxt_block.insert(BasicBlock.IS_FALSE_BLOCK, head_returned)
                all_tail_list.extend(tail_list)
            else:
                all_tail_list.append(basic_block)

            return head, all_tail_list







