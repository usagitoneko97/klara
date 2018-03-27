import ast


# basic class that represents tac (three address code)
class Tac:
    def __init__(self, assign_node):
        if isinstance(assign_node.value, ast.BinOp):
            self._target = assign_node.targets[0].id
            self.left_oprd = self.get_var_or_num(assign_node.value.left)
            self.right_oprd = self.get_var_or_num(assign_node.value.right)
            self.operator = assign_node.value.op.__class__.__name__
        elif isinstance(assign_node.value, ast.Name):
            self.single_oprd = assign_node.value.id

    @property
    def target(self):
        return self._target

    @target.setter
    def target(self, value):
        self._target = value

    @staticmethod
    def get_var_or_num(value):
        if isinstance(value, ast.Name):
            return value.id
        else:
            return str(value.n)


# class for handling the annotation of the ssa. eg., a = 0 --> a#0 = 0
class SsaSyntax:
    def __init__(self, var_str):
        self.var_str = var_str

    def ssa_annotate(self, number):
        """
        annotate the string. Eg., a --> a#0
        Don't annotate the number
        :param number:
        :return:
        """
        if self.represents_int(self.var_str) is False:
            hash_index = self.var_str.find('#')

            if hash_index != -1:
                self.var_str = self.var_str[0:hash_index + 1] + str(number)
            else:
                self.var_str += ('#' + str(number))

        return self.var_str

    def ssa_get_annotated_num(self):
        hash_index = self.var_str.find('#')
        if hash_index != -1:
            return int(self.var_str[hash_index+1:])

    def __str__(self):
        return self.var_str

    @staticmethod
    def represents_int(s):
        try:
            int(s)
            return True
        except ValueError:
            return False


# class that handling tac and ssa related stuff. Eg., convert a tac form to a ssa tac form
class TacSsa:
    def __init__(self):
        self._tac_list = []
        self._ssa_var_record = dict()
        pass

    def append_tac(self, assign_node):
        self._tac_list.append(Tac(assign_node))

    @property
    def tac_list(self):
        return self._tac_list

    @tac_list.setter
    def tac_list(self, value):
        self._tac_list = value

    def annotate_all_var(self, assign_tac, target_ssa_str, left_oprd_ssa_str, right_oprd_ssa_str):

        target_ssa_str.ssa_annotate(self._ssa_var_record[assign_tac.target])
        if assign_tac.right_oprd in self._ssa_var_record:
            right_oprd_ssa_str.ssa_annotate(self._ssa_var_record[assign_tac.right_oprd])
        else:
            self._ssa_var_record[assign_tac.right_oprd] = 0
        right_oprd_ssa_str.ssa_annotate(0)

        if assign_tac.left_oprd in self._ssa_var_record:
            left_oprd_ssa_str.ssa_annotate(self._ssa_var_record[assign_tac.left_oprd])
        else:
            self._ssa_var_record[assign_tac.left_oprd] = 0
        left_oprd_ssa_str.ssa_annotate(0)

        return target_ssa_str, left_oprd_ssa_str, right_oprd_ssa_str

    def convert_tac_2_ssa(self):
        """
        convert self._tac_list to ssa form
        :return:
        """
        # 1. if target var not exist, add the entry
        # 2. if target var exist, inc value
        # 3. always convert  left and right operand to ssa using current value
        for assign_tac in self._tac_list:
            if assign_tac.target in self._ssa_var_record:
                self._ssa_var_record[assign_tac.target] += 1
            else:
                self._ssa_var_record[assign_tac.target] = 0

            target_ssa_str = SsaSyntax(assign_tac.target)
            right_oprd_ssa_str = SsaSyntax(assign_tac.right_oprd)
            left_oprd_ssa_str = SsaSyntax(assign_tac.left_oprd)

            target_ssa_str, left_oprd_ssa_str, right_oprd_ssa_str = self.annotate_all_var(assign_tac,
                                                                                          target_ssa_str,
                                                                                          left_oprd_ssa_str,
                                                                                          right_oprd_ssa_str)

            assign_tac.target = str(target_ssa_str)
            assign_tac.left_oprd = str(left_oprd_ssa_str)
            assign_tac.right_oprd = str(right_oprd_ssa_str)
