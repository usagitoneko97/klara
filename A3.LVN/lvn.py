import ast


class Lvn:
    def __init__(self):
        self.value_dict = dict()
        self.lvnDict = dict()
        self.current_val = 0

    def lvn_optimize(self, as_tree):
        """
        perform lvn analysis on the asTree and return an optimized tree
        :param as_tree: the root of the tree
        :return: optimized tree
        """
        for assign_node in self._get_assign_class(as_tree):
            # check if its normal assignment or bin op
            if isinstance(assign_node.value, ast.BinOp):
                # form a string in form of "<valueNumber1><operator><valueNumber2>
                query_string = ""
                query_string += str(self._add_to_value_dict(assign_node.value.left.id))
                query_string += assign_node.value.op.__class__.__name__
                query_string += str(self._add_to_value_dict(assign_node.value.right.id))

                if query_string not in self.lvnDict:
                    self.lvnDict[query_string] = assign_node.targets[0].id
                else:
                    # it's in, replace the BinOp node with name
                    name_node = ast.Name()
                    name_node.id = self.lvnDict[query_string]
                    name_node.ctx = ast.Store()
                    assign_node.value = name_node

            # always assign new value number to left hand side
            self.value_dict[assign_node.targets[0].id] = self.current_val
            self.current_val += 1

        return as_tree

    @staticmethod
    def _get_assign_class(as_tree):
        for i in range(len(as_tree.body)):
            if isinstance(as_tree.body[i], ast.Assign):
                yield as_tree.body[i]

    def _add_to_value_dict(self, string):
        if string not in self.value_dict:
            self.value_dict[string] = self.current_val
            self.current_val += 1

        return self.value_dict[string]