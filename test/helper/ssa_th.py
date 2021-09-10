class ContainString(BaseException):
    pass


class SsaTestAssertion:
    def assertSsaVariable(self, ssa_var_real, ssa_var_expected):
        if ssa_var_expected is None:
            assert ssa_var_real is None
        else:
            assert str(ssa_var_real) == ssa_var_expected

    def assertSsa(self, ssa_real, ssa_expected):
        self.assertSsaVariable(ssa_real.target, ssa_expected.target)
        self.assertSsaVariable(ssa_real.left_oprd, ssa_expected.left_oprd)
        self.assertSsaVariable(ssa_real.right_oprd, ssa_expected.right_oprd)
        assert ssa_real.operator == ssa_expected.operator
        assert ssa_real.target_operator == ssa_expected.target_operator

    def assertSsaList(self, ssa_real_list, ssa_expected_list):
        assert len(ssa_real_list) == len(ssa_expected_list), "the number of ssa statements is not the same"
        for ssa_num in range(len(ssa_real_list)):
            self.assertSsa(ssa_real_list[ssa_num], ssa_expected_list[ssa_num])

    def assertBlockSsaList(self, real_block_list, expected_block_dict):
        # assert len(real_block_list) == len(expected_block_dict), "the number of blocks is not the same"
        for key, ssa_string in expected_block_dict.items():
            real_block = real_block_list.get_block_by_name(key)
            self.assertSsaCode(real_block.ssa_code, ssa_string)

    def assertSsaCode(self, real_ssa_code, ssa_list):
        if len(real_ssa_code.code_list) == 0 and len(ssa_list) == 0:
            return
        regular_str_to_test = ssa_list
        for ssa in real_ssa_code.code_list:
            ssa_str = repr(ssa).strip()
            assert ssa_str in regular_str_to_test, "{} does not contain in {}".format(ssa_str, regular_str_to_test)
