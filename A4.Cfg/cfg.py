import ast
import common


class BasicBlock:
    BLOCK_IF = 0
    BLOCK_WHILE = 1

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
        elif isinstance(self.ast_list[-1], ast.While):
            return self.BLOCK_WHILE


    def __repr__(self):
        s = ""
        for ast_node in self.ast_list:
            s += ast.dump(ast_node)

        return s


class Cfg:
    def __init__(self, as_tree=None, *basic_block_args):
        self.__else_flag__ = False
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
        if len(basic_block.ast_list) != 0:
            yield basic_block

        # self.add_basic_block(basic_block)

    @staticmethod
    def link_tail_to_cur_block(all_tail_list, basic_block):
        for tail in all_tail_list:
            tail.nxt_block.append(basic_block)

    def build_if_body(self, if_block):
        all_tail_list = []
        ast_if_node = if_block.ast_list[-1]
        head_returned, tail_list = self.parse(ast_if_node.body)

        if_block.nxt_block.insert(BasicBlock.IS_TRUE_BLOCK, head_returned)
        all_tail_list.extend(tail_list)

        head_returned, tail_list = self.parse(ast_if_node.orelse)
        if head_returned is not None:
            # has an else or elif
            if_block.nxt_block.insert(BasicBlock.IS_FALSE_BLOCK, head_returned)
            all_tail_list.extend(tail_list)
        else:
            # no else
            # link this to the next statement
            all_tail_list.append(if_block)

        return all_tail_list

    def build_while_body(self, while_block):
        all_tail_list = []
        ast_while_node = while_block.ast_list[-1]
        head_returned, tail_list = self.parse(ast_while_node.body)

        while_block.nxt_block.insert(BasicBlock.IS_TRUE_BLOCK, head_returned)
        for tail in tail_list:
            # link the tail back to itself (while operation
            tail.nxt_block.append(while_block)
        all_tail_list.append(while_block)
        return all_tail_list

    def parse(self, ast_body):
        head = None
        all_tail_list = []
        for basic_block in self.get_basic_block(ast_body):

            # link all the tail to the subsequent block
            if len(all_tail_list) == 0:
                head = basic_block
            else:
                pass
                self.link_tail_to_cur_block(all_tail_list, basic_block)

            all_tail_list = []
            self.add_basic_block(basic_block)
            if basic_block.get_block_type() == BasicBlock.BLOCK_IF:
                tail_list = self.build_if_body(basic_block)
                all_tail_list.extend(tail_list)

            elif basic_block.get_block_type() == BasicBlock.BLOCK_WHILE:
                tail_list = self.build_while_body(basic_block)
                all_tail_list.extend(tail_list)
                pass

            else:
                all_tail_list.append(basic_block)

        return head, all_tail_list



