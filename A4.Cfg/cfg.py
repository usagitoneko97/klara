import ast
import common


class RawBasicBlock:
    BLOCK_IF = 0
    BLOCK_WHILE = 1

    IS_TRUE_BLOCK = 0
    IS_FALSE_BLOCK = 1

    def __init__(self, start_line=None, end_line=None, block_end_type=None):
        self._start_line = start_line
        self._end_line = end_line
        self._block_end_type = block_end_type
        self.nxt_block_list = []

    def append_node(self, ast_node):
        self.ast_list.append(ast_node)

    def get_block_type(self):
        if isinstance(self.ast_list[-1], ast.If):
            return self.BLOCK_IF
        elif isinstance(self.ast_list[-1], ast.While):
            return self.BLOCK_WHILE

    @property
    def start_line(self):
        return self._start_line
        
    @start_line.setter
    def start_line(self, start_line):
        self._start_line = start_line

    @property
    def end_line(self):
        return self._end_line

    @end_line.setter
    def end_line(self, end_line):
        self._end_line = end_line

    @property
    def block_end_type(self):
        return self._block_end_type

    @block_end_type.setter
    def block_end_type(self, block_end_type):
        self._block_end_type = block_end_type
        
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
            self.as_tree = as_tree
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
        basic_block = RawBasicBlock(start_line=ast_body[0].lineno)
        for ast_node in ast_body:
            if basic_block.start_line is None:
                basic_block.start_line = ast_node.lineno
            basic_block.end_line = ast_node.lineno
            if common.is_if_stmt(ast_node) or common.is_while_stmt(ast_node):
                # self.add_basic_block(basic_block)
                basic_block.block_end_type = ast_node.__class__.__name__
                yield basic_block
                basic_block = RawBasicBlock()

        if basic_block.start_line is not None:
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

        if_block.nxt_block.insert(RawBasicBlock.IS_TRUE_BLOCK, head_returned)
        all_tail_list.extend(tail_list)

        head_returned, tail_list = self.parse(ast_if_node.orelse)
        if head_returned is not None:
            # has an else or elif
            if_block.nxt_block.insert(RawBasicBlock.IS_FALSE_BLOCK, head_returned)
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

        while_block.nxt_block.insert(RawBasicBlock.IS_TRUE_BLOCK, head_returned)
        for tail in tail_list:
            # link the tail back to itself (while operation
            tail.nxt_block.append(while_block)
        all_tail_list.append(while_block)
        return all_tail_list

    def parse(self, ast_body):
        head = None
        all_tail_list = []
        for basic_block in self.get_basic_block(ast_body):

            if len(all_tail_list) == 0:
                head = basic_block
            else:
                pass
                self.link_tail_to_cur_block(all_tail_list, basic_block)

            all_tail_list = []
            self.add_basic_block(basic_block)

            if basic_block.get_block_type() == RawBasicBlock.BLOCK_IF:
                tail_list = self.build_if_body(basic_block)
                all_tail_list.extend(tail_list)

            elif basic_block.get_block_type() == RawBasicBlock.BLOCK_WHILE:
                self.separate_and_link_last_ast()
                tail_list = self.build_while_body(self.block_list[-1])
                all_tail_list.extend(tail_list)

            else:
                all_tail_list.append(basic_block)

        return head, all_tail_list

    def separate_and_link_last_ast(self):
        while_basic_block = RawBasicBlock(ast_list=[(self.block_list[-1]).ast_list[-1]])
        (self.block_list[-1]).ast_list = (self.block_list[-1]).ast_list[:-1]
        self.block_list[-1].nxt_block.append(while_basic_block)
        self.add_basic_block(while_basic_block)

