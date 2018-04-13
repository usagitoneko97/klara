import ast
import common


class BasicBlock:
    def __init__(self):
        self.ast_list = []

    def append_node(self, ast_node):
        self.ast_list.append(ast_node)

    def __repr__(self):
        s = ""
        for ast_node in self.ast_list:
            s += ast.dump(ast_node)

        return s


class Cfg:
    def __init__(self, as_tree):
        self.block_list = []
        self.parse(as_tree)

    def parse(self, as_tree):
        basic_block = BasicBlock()
        for ast_node in as_tree.body:
            basic_block.append_node(ast_node)
            if common.is_call_func(ast_node):
                self.block_list.append(basic_block)
        self.block_list.append(basic_block)
