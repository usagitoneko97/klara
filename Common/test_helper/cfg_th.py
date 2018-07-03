import unittest


class CfgTestCase(unittest.TestCase):
    def assertCfgWithBasicBlocks(self, cfg_real, *args, block_links):
        from A4_CFG.cfg import Cfg, build_blocks
        cfg_expected = Cfg()

        block_list = build_blocks(*args, block_links=block_links)
        cfg_expected.block_list.extend(block_list)

        self.assertCfgEqual(cfg_real, cfg_expected)

    def assertCfgEqual(self, cfg_real, cfg_expected):
        self.assertEqual(len(cfg_real.block_list), len(cfg_expected.block_list),
                         "Number of real basic block {} is not the same as expected {}".format(len(cfg_real.block_list),
                                                                                               len(
                                                                                                   cfg_expected.block_list))
                         )
        for block_list_num in range(len(cfg_real.block_list)):
            self.assertBasicBlockEqual(cfg_real.block_list[block_list_num],
                                       cfg_expected.block_list[block_list_num],
                                       block_index=block_list_num)

    def assertBasicBlockEqual(self, basic_block_real, basic_block_expected, block_index=0):

        self.assertEqual(basic_block_real.block_end_type, basic_block_expected.block_end_type)

        self.assertStartEnd([basic_block_real.start_line, basic_block_real.end_line],
                            [basic_block_expected.start_line, basic_block_expected.end_line],
                            block_index)

        self.assertEqual(len(basic_block_real.nxt_block_list), len(basic_block_expected.nxt_block_list),
                         "total amount of next blocks between real and expected was not the same")
        for nxt_block_num in range(len(basic_block_real.nxt_block_list)):
            self.assertStartEnd([basic_block_real.nxt_block_list[nxt_block_num].start_line,
                                 basic_block_real.nxt_block_list[nxt_block_num].end_line],
                                [basic_block_expected.nxt_block_list[nxt_block_num].start_line,
                                 basic_block_expected.nxt_block_list[nxt_block_num].end_line],
                                block_index,
                                nxt_or_prev='next')

    def assertBasicBlockListEqual(self, block_real, block_expected):
        self.assertEqual(len(block_real), len(block_expected), 'the len of basic block is not the same')
        for block_num in range(len(block_real)):
            self.assertBasicBlockEqual(block_real[block_num], block_expected[block_num],
                                       block_index=block_num)

    def assertStartEnd(self, real_block, expected_block, block_index, nxt_or_prev=''):
        self.assertEqual(real_block[0], expected_block[0],
                         'On block {}, the start line is not the same at {}'.format(block_index, nxt_or_prev))

        self.assertEqual(real_block[1], expected_block[1],
                         'On block {}, the end line is not the same at {}'.format(block_index, nxt_or_prev))