import ast
from tac import Tac

class Lvn:
    def __init__(self):

        self.lvnDict = dict()
        self.value_number_dict = dict()
        self.current_val = 0
        self.alg_identities_dict = dict()
        self.build_alg_identities_dict()

    def build_alg_identities_dict(self):
        self.alg_identities_dict = {'#Mult2': '#Add#', '#Add#': '#Mult2', "#Add0": "#", "0Add#": "#", '#Sub0': "#",
                                    '#Mult0': '0', '0Mult#': '0'}

    @staticmethod
    def lvn_ast2arg_expr(assign_node):

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
            if isinstance(assign_node.value.op, ast.Add) or isinstance(assign_node.value.op, ast.Mult):
                if isinstance(assign_node.value.left, ast.Num) and  \
                   isinstance(assign_node.value.right, ast.Name):
                    return right_operand + assign_node.value.op.__class__.__name__ + left_operand

        return left_operand + assign_node.value.op.__class__.__name__ + right_operand

    @staticmethod
    def get_operands_on_assign_node(assign_node):
        """
        return the operands on assign node in string
        :param assign_node: the assign node in ast
        :return: left operands, right operands
        """
        if isinstance(assign_node.value.left, ast.Num):
            left_str = str(assign_node.value.left.n)
        else:
            left_str = assign_node.value.left.id

        if isinstance(assign_node.value.right, ast.Num):
            right_str = str(assign_node.value.right.n)
        else:
            right_str = assign_node.value.right.id

        return left_str, right_str, assign_node.targets[0].id

    def enumerate_and_store_var_in_dict(self, left_str, right_str, target_str):
        """
        enumerate the variable with their respective value number if the variable is not exist in the dict.The target of
        the assign node will always be enumerated. The current_val will be incremented
        :param left_str: left operands in string
        :param right_str: right operands in string
        :return: a list contain the value number for left and right operands in the order of [left, right]
        """
        query_string_list = [self._add_to_lvn_dict(left_str),
                             self._add_to_lvn_dict(right_str)]
        self.value_number_dict[target_str] = self.current_val
        self.current_val += 1

        return query_string_list

    def lvn_arg_expr2_stmt(self, arg_ident_str, left_str, right_str):
        """
        Convert no-variable form to normal statement with value number
        Eg., #Add2 --> aAdd2 --> 0Add2
        Note: assume value number for 'a' is 0
        :param arg_ident_str: the simplify form of the assignment. Eg., #Add2
        :param left_str: The left operand
        :param right_str: The right operand
        :return: assign statement with value number
        """
        query_str = self.alg_identities_dict[arg_ident_str]

        if not self.represents_int(left_str):
            query_str = query_str[:-1].replace("#", str(self.value_number_dict[left_str])) + query_str[
                -1]
            query_str = query_str[0] + query_str[1:].replace("#", str(self.value_number_dict[left_str]))
        else:
            query_str = query_str[:-1].replace("#", str(self.value_number_dict[right_str])) + query_str[
                -1]
            query_str = query_str[0] + query_str[1:].replace("#", str(self.value_number_dict[right_str]))

        return query_str

    def lvn_optimize_alg_identities(self, assign_node):
        """
        optimize the statement by some algebraic identities, eg., a + 0 = a.
        1. It will convert the assign statement to a no-variable string. Eg., a + 0 --> #Add0
        2. Perform the search on the alg_identities dict to determine whether the expression can be simplify
        3. If key exist in the dict, replace the right hand side expression with the value of the key. Eg., a + 0 --> a
        :param assign_node: one assign statement
        :return:
        """
        arg_ident_str = self.lvn_ast2arg_expr(assign_node)

        if arg_ident_str in self.alg_identities_dict:
            # always insert value number for left hand side
            # 2 cases, - value returned is single variable, then we can replace it,
            #          - value returned is expr, then we have to find the expr existed or not before replacing
            if len(self.alg_identities_dict[arg_ident_str]) == 1:
                # replace it
                if self.alg_identities_dict[arg_ident_str] == '#':
                    name_node = ast.Name()
                    name_node.ctx = ast.Store()
                    # It will replace with either left hand side operand or right hand side operand.
                    # Eg., a + 0 --> a  /  0 + b -- b
                    if isinstance(assign_node.value.left, ast.Name):
                        name_node.id = assign_node.value.left.id
                    if isinstance(assign_node.value.right, ast.Name):
                        name_node.id = assign_node.value.right.id
                    assign_node.value = name_node

                else:
                    num_node = ast.Num(n=int(self.alg_identities_dict[arg_ident_str]))
                    assign_node.value = num_node

            else:
                left_str, right_str, _ = self.get_operands_on_assign_node(assign_node)

                # Get the string that represent the assignment in form of value-number
                query_str = self.lvn_arg_expr2_stmt(arg_ident_str, left_str, right_str)

                if query_str in self.lvnDict:
                    if self.lvnDict[query_str] in self.value_number_dict.values():
                        # value number has an associated variable
                        name_node = ast.Name()
                        # get the variable name by the value number
                        name_node.id = list(self.value_number_dict.keys())[
                            list(self.value_number_dict.values()).index(self.lvnDict[query_str])]
                        name_node.ctx = ast.Store()
                        assign_node.value = name_node

        return assign_node

    @staticmethod
    def sort_operands_by_value_number(query_string_list, assign_node):
        """
        only sort the operands by value number in ascending order when the binary operator is either '+' or '*'
        :param query_string_list: a list that contain left and right operand value number.
        :param assign_node: the assign statement in ast form
        :return: sorted query_string_list
        """
        if isinstance(assign_node.value.op, ast.Add) or isinstance(assign_node.value.op, ast.Mult):
            # only sort when its + or * since it can interchange
            query_string_list.sort()

        return query_string_list

    @staticmethod
    def build_value_number_expr(query_string_list, assign_node):
        """
        build a string to represent the statement by value number.
        Eg., 2Add0, 0Mult1, where 0, 1, 2 is the value number of a particular variable
        :param query_string_list: list that contain left and right operand value number.
        :param assign_node: the assign statement in ast form
        :return: string of assignment with value number
        """
        query_string = str(query_string_list[0])
        query_string += assign_node.value.op.__class__.__name__
        query_string += str(query_string_list[1])
        return query_string

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
                tac_stmt = Tac(assign_node)

                query_string_list = self.enumerate_and_store_var_in_dict(tac_stmt.left_oprd,
                                                                         tac_stmt.right_oprd, tac_stmt.target)

                assign_node = self.lvn_optimize_alg_identities(assign_node)

                if isinstance(assign_node.value, ast.BinOp):
                    # sort it to simplify the problem like "a + 0" = "0 + a"
                    query_string_list = self.sort_operands_by_value_number(query_string_list, assign_node)

                    # build a string to represent the statement by value number.
                    # Eg., 2Add0, 0Mult1, where 0, 1, 2 is the value number of a particular variable
                    query_string = self.build_value_number_expr(query_string_list, assign_node)

                    if query_string not in self.lvnDict:
                        # assign the value number to the hash key ("0Add1 : 2)
                        self.lvnDict[query_string] = self.current_val - 1

                    else:
                        # it's in, replace the BinOp node with name
                        if self.lvnDict[query_string] in self.value_number_dict.values():
                            # value number has an associated variable
                            name_node = ast.Name(id=list(self.value_number_dict.keys())[
                                                    list(self.value_number_dict.values()).
                                                    index(self.lvnDict[query_string])],
                                                 ctx=ast.Store())
                            assign_node.value = name_node
            else:
                self.value_number_dict[assign_node.targets[0].id] = self.current_val
                self.current_val += 1
            # always assign new value number to left hand side

        return as_tree

    @staticmethod
    def represents_int(s):
        try:
            int(s)
            return True
        except ValueError:
            return False

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