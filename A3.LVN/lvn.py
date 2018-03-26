import ast


class Lvn:
    def __init__(self):

        self.lvnDict = dict()
        self.value_number_dict = dict()
        self.current_val = 0
        self.alg_identities_dict = dict()
        self.build_alg_identities_dict()

    def build_alg_identities_dict(self):
        self.alg_identities_dict = {'2Mult#': '#Add#', '#Add#': '#Mult2', "#Add0": "#", "0Add#": "#", '#Sub0': "#",
                                    '#Mult0': '0', '0Mult#': '0'}

    @staticmethod
    def lvn_ast2arg_expr(assign_node):
        """
        :param: assign_node: the whole assign statement in ast form
        convert ast expression eg., 2 + a to general expression to search on alg identities dict. Eg., 2 + #
        important points :
            1. convert variable to general symbol, '#'
            2. Number will not be converted
            3. '-'  symbol is used to differentiate between 2 different variables
            4. variable will always appears at the left hand side operand over number to simplify the dictionary
                entries.
        :return: formatted general expression string to search on alg identities dict
        """
        if isinstance(assign_node.value, ast.BinOp):
            if isinstance(assign_node.value.left, ast.Num):
                # number will not be converted
                left_operand = str(assign_node.value.left.n)

            else:
                # substitute var with '#'
                left_operand = '#'

            if isinstance(assign_node.value.right, ast.Num):
                # number will not be converted
                right_operand = str(assign_node.value.right.n)
            else:
                # substitute var with '#'
                right_operand = '#'

            if left_operand == '#' and right_operand == '#':
                # check if the variable is same, only then can assign to the same symbol
                if assign_node.value.left.id != assign_node.value.right.id:
                    right_operand = '_'

            # reorder the left and right operand ( 3 + a --> a + 3)
            if isinstance(assign_node.value.left, ast.Num) and  \
                isinstance(assign_node.value.right, ast.Name):
                return right_operand + assign_node.value.op.__class__.__name__ + left_operand

        return left_operand + assign_node.value.op.__class__.__name__ + right_operand

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
                # ordering the value number in ascending order
                left_str_alg_real = ""
                right_str_alg_real = ""
                if isinstance(assign_node.value.left, ast.Num):
                    left_str = str(assign_node.value.left.n)
                    left_str_alg = left_str
                else:
                    left_str = assign_node.value.left.id
                    left_str_alg = '#'
                    left_str_alg_real = left_str

                if isinstance(assign_node.value.right, ast.Num):
                    right_str = str(assign_node.value.right.n)
                    right_str_alg = right_str
                else:
                    right_str = assign_node.value.right.id
                    right_str_alg = '#'
                    right_str_alg_real = right_str

                if isinstance(assign_node.value.left, ast.Name) and isinstance(assign_node.value.right, ast.Name):
                    if assign_node.value.right.id == assign_node.value.left.id:
                        left_str_alg = '#'
                        right_str_alg = '#'
                    else:
                        left_str_alg = ''
                        right_str_alg = ''

                query_string_list = [self._add_to_lvn_dict(left_str),
                                     self._add_to_lvn_dict(right_str)]

                expr_string = left_str_alg + assign_node.value.op.__class__.__name__ + right_str_alg
                arg_ident_str = self.lvn_ast2arg_expr(assign_node)

                if expr_string in self.alg_identities_dict:
                    # always insert value number for left hand side
                    self.value_number_dict[assign_node.targets[0].id] = self.current_val
                    self.current_val += 1
                    # 2 cases, - value returned is single variable, then we can replace it,
                    #          - value returned is expr, then we have to find the expr existed or not before replacing
                    if len(self.alg_identities_dict[expr_string]) == 1:
                        # replace it
                        if self.alg_identities_dict[expr_string] == '#':
                            name_node = ast.Name()
                            name_node.ctx = ast.Store()
                            if left_str_alg_real != "":
                                name_node.id = left_str_alg_real
                            else:
                                name_node.id = right_str_alg_real
                            assign_node.value = name_node

                        else:
                            num_node = ast.Num(n=int(self.alg_identities_dict[expr_string]))
                            assign_node.value = num_node
                        continue

                    else:
                        query_str = self.alg_identities_dict[expr_string]
                        if right_str_alg_real != "":
                            if query_str[0] == '#':
                                query_str = str(query_string_list[1]) + query_str[1:]
                            if query_str[-1] == '#':
                                query_str = query_str[:-1] + str(query_string_list[1])
                        else:
                            if query_str[0] == '#':
                                query_str = str(query_string_list[0]) + query_str[1:]
                            if query_str[-1] == '#':
                                query_str = query_str[:-1] + str(query_string_list[0])

                        if query_str in self.lvnDict:
                            # assign the value number to the hash key ("0Add1 : 2)
                            if self.lvnDict[query_str] in self.value_number_dict.values():
                                # value number has an associated variable
                                name_node = ast.Name()
                                name_node.id = list(self.value_number_dict.keys())[
                                    list(self.value_number_dict.values()).index(self.lvnDict[query_str])]
                                name_node.ctx = ast.Store()
                                assign_node.value = name_node

                                continue

                if isinstance(assign_node.value.op, ast.Add) or isinstance(assign_node.value.op, ast.Mult):
                    # only sort when its + or * since it can interchange
                    query_string_list.sort()

                query_string = str(query_string_list[0])
                query_string += assign_node.value.op.__class__.__name__
                query_string += str(query_string_list[1])

                if query_string not in self.lvnDict:
                    # assign the value number to the hash key ("0Add1 : 2)
                    self.lvnDict[query_string] = self.current_val
                else:
                    # it's in, replace the BinOp node with name
                    if self.lvnDict[query_string] in self.value_number_dict.values():
                        # value number has an associated variable
                        name_node = ast.Name()
                        name_node.id = list(self.value_number_dict.keys())[
                            list(self.value_number_dict.values()).index(self.lvnDict[query_string])]
                        name_node.ctx = ast.Store()
                        assign_node.value = name_node

            # always assign new value number to left hand side

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