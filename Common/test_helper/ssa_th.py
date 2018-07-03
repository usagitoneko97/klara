import unittest


class ContainString(BaseException):
    pass


class SsaTestCase(unittest.TestCase):
    def assertBlockSsaList(self, real_block_list, expected_block_dict):
        self.assertEqual(len(real_block_list), len(expected_block_dict),
                         "the number of blocks is not the same")
        for key, ssa_string_list in expected_block_dict.items():
            real_block = real_block_list.get_block_by_name(key)
            try:
                if isinstance(ssa_string_list, list):
                    for ssa_string in ssa_string_list:
                        if self.assertSsaCode(real_block.ssa_code, ssa_string):
                            raise ContainString
                else:
                    if self.assertSsaCode(real_block.ssa_code, ssa_string_list):
                        raise ContainString

            except ContainString:
                continue

            self.fail(f"expected ssa string {ssa_string_list} is not the same with :{str(real_block.ssa_code)}")

    def assertSsaCode(self, real_ssa_code, ssa_string):
        for ssa in real_ssa_code.code_list:
            if str(ssa) not in ssa_string:
                return False

        return True