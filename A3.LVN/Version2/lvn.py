from ssa import Ssa, SsaCode
from lvn_dict import LvnDict

class Lvn:
    operator_dict = {'Add': '+', 'Sub': '-', 'Mult': '*', 'Div': '/', 'BitOr': '|', 'BitXor': '^', 'BitAnd': '&',
                     'Lt': '<', 'Gt': '>'}

    def __init__(self):

        self.lvnDict = dict()
        self.value_number_dict = dict()
        self.current_val = 0
        self.alg_identities_dict = dict()
        self.lvn_dict = LvnDict()

    def lvn_code_to_ssa_code(self):
        ssa_code = SsaCode()
        for lvn_code_tuple in self.lvn_dict.lvn_code_tuples_list:
            ssa = Ssa()
            ssa.target = self.lvn_dict.variable_dict.val_num_var_list[lvn_code_tuple[0]]
            # left is constant
            if lvn_code_tuple[4] == 1:
                ssa.left_oprd = lvn_code_tuple[1]
                if lvn_code_tuple[2] is not None and lvn_code_tuple[3] is not None:
                    ssa.operator = self.get_real_operator(lvn_code_tuple[2])
                    ssa.right_oprd = self.lvn_dict.variable_dict.val_num_var_list[lvn_code_tuple[3]]
            elif lvn_code_tuple[4] == 2:
                ssa.right_oprd = lvn_code_tuple[3]
                if lvn_code_tuple[2] is not None and lvn_code_tuple[3] is not None:
                    ssa.operator = self.get_real_operator(lvn_code_tuple[2])
                    ssa.left_oprd = self.lvn_dict.variable_dict.val_num_var_list[lvn_code_tuple[1]]
                # ssa.left_oprd = self.lvn_dict.variable_dict.val_num_var_list[lvn_code_tuple[1]]
            else:
                ssa.left_oprd = self.lvn_dict.variable_dict.val_num_var_list[lvn_code_tuple[1]]
                if lvn_code_tuple[2] is not None and lvn_code_tuple[3] is not None:
                    ssa.operator = self.get_real_operator(lvn_code_tuple[2])
                    ssa.right_oprd = self.lvn_dict.variable_dict.val_num_var_list[lvn_code_tuple[3]]

            ssa_code.code_list.append(ssa)

        return ssa_code

    def get_real_operator(self, string):
        return type(self).operator_dict.get(string)

    def is_constant(self, lvn_code_tuple):
        if lvn_code_tuple[4] == 1:
            return True
        return False

    def optimize(self, ssa_code):
        for ssa in ssa_code:
            # building the variable dictionary
            self.lvn_dict.enumerate_rhs(ssa)
            # general_expr_str = self.lvn_dict.get_general_expr(ssa)
            # expr = self.lvn_dict.get_alg_ident(general_expr_str)
            # ssa.replace_rhs_expr(expr)
            simple_expr = self.lvn_dict.get_simple_expr(ssa)
            self.lvn_dict.enumerate_lhs(ssa)
            self.lvn_dict.add_simple_expr(simple_expr)

        ssa_optimized_code = self.lvn_code_to_ssa_code()
        return ssa_optimized_code