import ast


class Lvn:
    def __init__(self):

        self.lvnDict = dict()
        self.value_number_dict = dict()
        self.current_val = 0

    def lvn_optimize(self, as_tree):
        """
        perform lvn analysis on the asTree and return an optimized tree
        :param as_tree: the root of the tree
        :return: optimized tree
        """
        for assign_node in self._get_assign_class(as_tree):

            # always assign new value number to left hand side
            self.value_number_dict[assign_node.targets[0].id] = self.current_val
            self.current_val += 1
            # check if its normal assignment or bin op
            if isinstance(assign_node.value, ast.BinOp):
                # form a string in form of "<valueNumber1><operator><valueNumber2>
                # ordering the value number in ascending order
                query_string_list = [self._add_to_lvn_dict(assign_node.value.left.id),
                                     self._add_to_lvn_dict(assign_node.value.right.id)]
                if isinstance(assign_node.value.op, ast.Add) or isinstance(assign_node.value.op, ast.Mult):

                    # only sort when its + or * since it can interchange
                    query_string_list.sort()

                query_string = str(query_string_list[0])
                query_string += assign_node.value.op.__class__.__name__
                query_string += str(query_string_list[1])
                if query_string not in self.lvnDict:
                    # assign the value number to the hash key ("0Add1 : 2)
                    self.lvnDict[query_string] = self.value_number_dict[assign_node.targets[0].id]
                else:
                    # it's in, replace the BinOp node with name
                    if self.lvnDict[query_string] in self.value_number_dict.values():
                        # value number has an associated variable
                        name_node = ast.Name()
                        name_node.id = list(self.value_number_dict.keys())[list(self.value_number_dict.values()).index(self.lvnDict[query_string])]
                        name_node.ctx = ast.Store()
                        assign_node.value = name_node

        return as_tree

    @staticmethod
    def _get_assign_class(as_tree):
        for i in range(len(as_tree.body)):
            if isinstance(as_tree.body[i], ast.Assign):
                yield as_tree.body[i]

    def _add_to_lvn_dict(self, string):
        if string not in self.value_number_dict:
            self.value_number_dict[string] = self.current_val
            self.current_val += 1

        return self.value_number_dict[string]