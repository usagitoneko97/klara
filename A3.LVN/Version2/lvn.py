from ssa import Ssa, SsaCode, SsaVariable
from lvn_dict import LvnDict
from common import *
from algebraic_identities import AlgIdent


class Lvn:

    def __init__(self):
        self.lvn_dict = LvnDict()
        self.alg_ident = AlgIdent()

    def optimize(self, ssa_code):
        for ssa in ssa_code:
            self.lvn_dict.variable_dict.enumerate(ssa)
            ssa.left_oprd, ssa.operator, ssa.right_oprd = self.alg_ident.optimize_alg_identities(ssa.left_oprd,
                                                                                                 ssa.operator,
                                                                                                 ssa.right_oprd)

            lvn_stmt = self.lvn_dict.get_lvn_stmt(ssa)
            if lvn_stmt.is_simple_assignment():
                # try to replace the left operand
                if self.lvn_dict.variable_dict.is_both_var_same(lvn_stmt.target, lvn_stmt.left):
                    continue
                lvn_stmt.left = self.lvn_dict.simple_assign_dict.find_substitute(lvn_stmt.left)
                if self.lvn_dict.variable_dict.is_both_var_same(lvn_stmt.target, lvn_stmt.left):
                    continue
                self.lvn_dict.simple_assign_dict.update_simp_assgn(lvn_stmt.target, lvn_stmt.left)

            else:
                lvn_stmt.left = self.lvn_dict.simple_assign_dict.find_substitute(lvn_stmt.left)
                lvn_stmt.right = self.lvn_dict.simple_assign_dict.find_substitute(lvn_stmt.right)
                if self.lvn_dict.variable_dict.is_const(lvn_stmt.left) and \
                   self.lvn_dict.variable_dict.is_const(lvn_stmt.right):
                    # fold it by eval the string
                    self.fold_lvn_stmt(lvn_stmt)

                else:
                    lvn_stmt.reorder_selected_operands()
                    lvn_stmt = self.lvn_dict.find_substitute(lvn_stmt)

                    if not lvn_stmt.is_simple_assignment():
                        self.lvn_dict.add_expr(lvn_stmt.get_expr(), lvn_stmt.target)
                    else:
                        # it's simple expr, add into simple_assign_dict
                        if self.lvn_dict.variable_dict.is_both_var_same(lvn_stmt.target, lvn_stmt.left):
                            continue
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

    def fold_lvn_stmt(self, lvn_stmt):
        eval_string = str(self.lvn_dict.variable_dict.get_variable(lvn_stmt.left)) + \
                      operator_dict.get(lvn_stmt.operator) + \
                      str(self.lvn_dict.variable_dict.get_variable(lvn_stmt.right))
        val_after_folded = eval(eval_string)
        lvn_stmt.left = self.lvn_dict.variable_dict._add_to_variable_dict(SsaVariable(val_after_folded))
        lvn_stmt.operator = None
        lvn_stmt.right = None
        self.lvn_dict.simple_assign_dict.update_simp_assgn(lvn_stmt.target, lvn_stmt.left)

    @staticmethod
    def get_operand_type(lvn_code_tuple):
        return lvn_code_tuple[4]

    def get_real_operator(self, string):
        return operator_dict.get(string)

    @staticmethod
    def is_constant(lvn_code_tuple):
        if lvn_code_tuple[4] == 1:
            return True
        return False
