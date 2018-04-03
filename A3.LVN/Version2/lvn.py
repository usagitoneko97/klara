from ssa import Ssa, SsaCode
from lvn_dict import LvnDict
from common import *


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

            lvn_stmt = self.lvn_dict.get_lvn_stmt(ssa)
            if lvn_stmt.is_simple_assignment():
                # try to replace the left operand
                lvn_stmt.left = self.lvn_dict.simple_assign_dict.find_substitute(lvn_stmt.left)
                self.lvn_dict.simple_assign_dict.update_simp_assgn(lvn_stmt.target, lvn_stmt.left)

            else:
                lvn_stmt.left = self.lvn_dict.simple_assign_dict.find_substitute(lvn_stmt.left)
                lvn_stmt.right = self.lvn_dict.simple_assign_dict.find_substitute(lvn_stmt.right)
                lvn_stmt = self.lvn_dict.find_substitute(lvn_stmt)
                if not lvn_stmt.is_simple_assignment():
                    self.lvn_dict.add_expr(lvn_stmt.get_expr(), lvn_stmt.target)
                else:
                    # it's simple expr, add into simple_assign_dict
                    self.lvn_dict.simple_assign_dict.update_simp_assgn(lvn_stmt.target, lvn_stmt.left)

            self.lvn_dict.lvn_code_tuples_list.append_lvn_stmt(lvn_stmt)

        ssa_optimized_code = self.lvn_code_to_ssa_code()
        return ssa_optimized_code

    def lvn_code_to_ssa_code(self):
        ssa_code = SsaCode()
        for lvn_code_tuple in self.lvn_dict.lvn_code_tuples_list:
            target, left, op, right = None, None, None, None

            target = self.lvn_dict.variable_dict.val_num_var_list[lvn_code_tuple[0]]
            # left is constant
            left = self.lvn_dict.variable_dict.val_num_var_list[lvn_code_tuple[1]]
            if lvn_code_tuple[2] is not None and lvn_code_tuple[3] is not None:
                op = self.get_real_operator(lvn_code_tuple[2])
                right = self.lvn_dict.variable_dict.val_num_var_list[lvn_code_tuple[3]]

            ssa = Ssa(target, left, op, right)
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
