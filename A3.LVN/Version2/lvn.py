from ssa import Ssa, SsaCode
from lvn_dict import LvnDict
import common


class Lvn:
    operator_dict = {'Add': '+', 'Sub': '-', 'Mult': '*', 'Div': '/', 'BitOr': '|', 'BitXor': '^', 'BitAnd': '&',
                     'Lt': '<', 'Gt': '>', 'FloorDiv': '//', 'Mod': '%', 'Pow': '^', 'LShift': '<<', 'RShift': '>>',
                     'Eq': '==', 'NotEq': '!=', 'LtE': '<=', 'GtE': '>=', 'Is' :'is', 'IsNot': 'is not', 'In': 'in',
                     'NotIn': 'not in'}

    def __init__(self):
        self.lvn_dict = LvnDict()

    def optimize(self, ssa_code):
        for ssa in ssa_code:
            self.lvn_dict.variable_dict.enumerate(ssa)

            alg_expr = self.lvn_dict.get_alg_expr(ssa)
            if alg_expr.is_simple_expr():
                # try to replace the left operand
                if alg_expr.operand_type != LEFT_OPERATOR_CONSTANT:
                    alg_expr.left = self.lvn_dict.simple_assign_dict.find_substitute(alg_expr.left)
                self.lvn_dict.simple_assign_dict.update_simp_assgn(alg_expr.target, alg_expr.left)

            else:
                alg_expr.left = self.lvn_dict.simple_assign_dict.find_substitute(alg_expr.left)
                alg_expr.right = self.lvn_dict.simple_assign_dict.find_substitute(alg_expr.right)
                alg_expr = self.lvn_dict.find_substitute(alg_expr)

            self.lvn_dict.lvn_code_tuples_list.append_alg_expr(alg_expr)

        ssa_optimized_code = self.lvn_code_to_ssa_code()
        return ssa_optimized_code

    def lvn_code_to_ssa_code(self):
        ssa_code = SsaCode()
        for lvn_code_tuple in self.lvn_dict.lvn_code_tuples_list:
            ssa = Ssa()
            ssa.target = self.lvn_dict.variable_dict.val_num_var_list[lvn_code_tuple[0]]
            # left is constant
            if self.get_operand_type(lvn_code_tuple) == common.LEFT_OPERATOR_CONSTANT:
                ssa.left_oprd = lvn_code_tuple[1]
                if lvn_code_tuple[2] is not None and lvn_code_tuple[3] is not None:
                    ssa.operator = self.get_real_operator(lvn_code_tuple[2])
                    ssa.right_oprd = self.lvn_dict.variable_dict.val_num_var_list[lvn_code_tuple[3]]

            elif self.get_operand_type(lvn_code_tuple) == common.RIGHT_OPERATOR_CONSTANT:
                ssa.right_oprd = lvn_code_tuple[3]
                if lvn_code_tuple[2] is not None and lvn_code_tuple[3] is not None:
                    ssa.operator = self.get_real_operator(lvn_code_tuple[2])
                    ssa.left_oprd = self.lvn_dict.variable_dict.val_num_var_list[lvn_code_tuple[1]]
            else:
                ssa.left_oprd = self.lvn_dict.variable_dict.val_num_var_list[lvn_code_tuple[1]]
                if lvn_code_tuple[2] is not None and lvn_code_tuple[3] is not None:
                    ssa.operator = self.get_real_operator(lvn_code_tuple[2])
                    ssa.right_oprd = self.lvn_dict.variable_dict.val_num_var_list[lvn_code_tuple[3]]

            ssa_code.code_list.append(ssa)

        return ssa_code

    @staticmethod
    def get_operand_type(lvn_code_tuple):
        return lvn_code_tuple[4]

    def get_real_operator(self, string):
        return type(self).operator_dict.get(string)

    @staticmethod
    def is_constant(lvn_code_tuple):
        if lvn_code_tuple[4] == 1:
            return True
        return False
