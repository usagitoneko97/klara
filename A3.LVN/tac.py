import ast


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
        print("setter called")
        self._target = value

    @staticmethod
    def get_var_or_num(value):
        if isinstance(value, ast.Name):
            return value.id
        else:
            return str(value.n)