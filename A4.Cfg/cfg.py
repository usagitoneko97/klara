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
        self.prev_block_list = []
        self.dominates_list = []
        self.walk_record = []

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
        s = "Block from line {} to {}".format(self.start_line, self.end_line)
        return s


class Cfg:
    def __init__(self, as_tree=None, *basic_block_args):
        self.__else_flag__ = False
        self.block_list = []
        self.walk_record = []
        self.delete_record = []

        if as_tree is not None:
            self.as_tree = as_tree
            self.root, _ = self.parse(as_tree.body)

        if len(basic_block_args) != 0:
            for basic_block in basic_block_args:
                self.add_basic_block(basic_block)

    def add_basic_block(self, basic_block):
        if basic_block.start_line is not None:
            self.block_list.append(basic_block)

    def walk_block(self, basic_block):
        """
        yield nodes from bottom
        :return:
        """
        if basic_block is None:
            return
        self.walk_record.append(basic_block)
        for next_block in basic_block.nxt_block_list:
            if next_block not in self.walk_record and next_block is not None:
                yield from self.walk_block(next_block)
        yield basic_block

    @staticmethod
    def get_basic_block(ast_body):
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

    def get_ast_node(self, ast_tree, lineno):
        for node in ast.iter_child_nodes(ast_tree):

            if node.lineno == lineno:
                return node

            if isinstance(node, ast.If) or isinstance(node, ast.While):
                node_return = self.get_ast_node(node, lineno)
                if node_return is not None:
                    return node_return
                continue

        return None

    def link_tail_to_cur_block(self, all_tail_list, basic_block):
        for tail in all_tail_list:
            self.connect_2_blocks(tail, basic_block)

    def build_if_body(self, if_block):
        all_tail_list = []
        ast_if_node = self.get_ast_node(self.as_tree, if_block.end_line)
        head_returned, tail_list = self.parse(ast_if_node.body)

        self.connect_2_blocks(if_block, head_returned)
        all_tail_list.extend(tail_list)

        head_returned, tail_list = self.parse(ast_if_node.orelse)
        if head_returned is not None:
            # has an else or elif
            self.connect_2_blocks(if_block, head_returned)
            all_tail_list.extend(tail_list)
        else:
            # no else
            # link this to the next statement
            all_tail_list.append(if_block)

        return all_tail_list

    def build_while_body(self, while_block):
        all_tail_list = []
        ast_while_node = self.get_ast_node(self.as_tree, while_block.end_line)
        head_returned, tail_list = self.parse(ast_while_node.body)

        self.connect_2_blocks(while_block, head_returned)
        self.link_tail_to_cur_block(tail_list, while_block)
        all_tail_list.append(while_block)
        return all_tail_list

    def parse(self, ast_body):
        head = None
        all_tail_list = []
        if len(ast_body) == 0:
            return head, all_tail_list
        for basic_block in self.get_basic_block(ast_body):

            if len(all_tail_list) == 0:
                head = basic_block
            else:
                pass
                self.link_tail_to_cur_block(all_tail_list, basic_block)

            all_tail_list = []
            self.add_basic_block(basic_block)

            if basic_block.block_end_type == 'If':
                tail_list = self.build_if_body(basic_block)
                all_tail_list.extend(tail_list)

            elif basic_block.block_end_type == 'While':
                while_block = self.separate_while_block(basic_block)

                tail_list = self.build_while_body(while_block)
                all_tail_list.extend(tail_list)

            else:
                all_tail_list.append(basic_block)

        return head, all_tail_list

    def separate_block(self, basic_block):
        separated_block = RawBasicBlock(basic_block.end_line, basic_block.end_line)
        basic_block.end_line -= 1
        self.connect_2_blocks(basic_block, separated_block)
        return separated_block

    def separate_while_block(self, basic_block):
        while_block = self.separate_block(basic_block)

        while_block.block_end_type = 'While'
        basic_block.block_end_type = None
        self.add_basic_block(while_block)
        return while_block

    @staticmethod
    def connect_2_blocks(block1, block2):
        """
        connect block 1 to block 2
        :param block1:
        :param block2:
        :return:
        """
        block1.nxt_block_list.append(block2)
        block2.prev_block_list.append(block1)

    @staticmethod
    def is_blocks_same(block1, block2):
        return str(block1) == str(block2)

    def delete_node(self, root,  block_to_delete):
        if self.is_blocks_same(root, block_to_delete) or root is None:
            return None

        self.delete_record.append(root)
        for next_block_num in range(len(root.nxt_block_list)):
            if root.nxt_block_list[next_block_num] not in self.delete_record:
                root.nxt_block_list[next_block_num] = self.delete_node(root.nxt_block_list[next_block_num],
                                                                       block_to_delete)

        # no child left, return yourself
        return root

