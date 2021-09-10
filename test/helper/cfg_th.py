import itertools

from klara.core.cfg import Cfg, PhiStubBlock, TempAssignBlock


class AssertTrueBasicBlock(Exception):
    pass


class CfgTestAssertion:
    def assertCfgWithBasicBlocks(self, cfg_real, *args, **kwargs):
        block_links = kwargs.get("block_links")
        name_required = kwargs.get("name_required")
        from klara.core.cfg import Cfg, build_blocks

        cfg_expected = Cfg()

        block_list = build_blocks(*args, block_links=block_links)
        cfg_expected.block_list.extend(block_list)
        self.assertBasicBlockListEqual(cfg_real.block_list, block_list, name_required)

    def remove_placeholder_block(self, block_list):
        blk_list = []
        for blk in block_list:
            if isinstance(blk, PhiStubBlock) or isinstance(blk, TempAssignBlock):
                self.remove_block(blk)
            else:
                blk_list.append(blk)
        return blk_list

    def assertCfgEqual(self, cfg_real, cfg_expected):
        self.assertEqual(
            len(cfg_real.block_list),
            len(cfg_expected.block_list),
            "Number of real basic block {} is not the same as expected {}".format(
                len(cfg_real.block_list), len(cfg_expected.block_list)
            ),
        )
        for block_list_num in range(len(cfg_real.block_list)):
            self.assertBasicBlockEqual(
                cfg_real.block_list[block_list_num], cfg_expected.block_list[block_list_num], block_index=block_list_num
            )

    def assertBasicBlockEqual(self, basic_block_real, basic_block_expected, block_index=0):

        assert basic_block_real.block_end_type == basic_block_expected.block_end_type

        self.assertStartEnd(
            [basic_block_real.start_line, basic_block_real.end_line],
            [basic_block_expected.start_line, basic_block_expected.end_line],
            block_index,
        )

        assert len(basic_block_real.nxt_block_list) == len(
            basic_block_expected.nxt_block_list
        ), "total amount of next blocks between real and expected was not the same"
        for nxt_block_num in range(len(basic_block_real.nxt_block_list)):
            self.assertStartEnd(
                [
                    basic_block_real.nxt_block_list[nxt_block_num].start_line,
                    basic_block_real.nxt_block_list[nxt_block_num].end_line,
                ],
                [
                    basic_block_expected.nxt_block_list[nxt_block_num].start_line,
                    basic_block_expected.nxt_block_list[nxt_block_num].end_line,
                ],
                block_index,
                nxt_or_prev="next",
            )

    def is_basic_block_equal(
        self, basic_block_real, basic_block_expected, name_required=True, assert_link=True, preserve_seq=True
    ):
        if name_required and basic_block_real.name != basic_block_expected.name:
            return False

        if basic_block_real.block_end_type != basic_block_expected.block_end_type:
            return False

        if not self.is_start_end(
            [basic_block_real.start_line, basic_block_real.end_line],
            [basic_block_expected.start_line, basic_block_expected.end_line],
        ):
            return False

        if assert_link is True:
            if len(basic_block_real.nxt_block_list) != len(basic_block_expected.nxt_block_list):
                return False

            if preserve_seq is True:
                for nxt_block_num in range(len(basic_block_real.nxt_block_list)):
                    if not self.is_start_end(
                        [
                            basic_block_real.nxt_block_list[nxt_block_num].start_line,
                            basic_block_real.nxt_block_list[nxt_block_num].end_line,
                        ],
                        [
                            basic_block_expected.nxt_block_list[nxt_block_num].start_line,
                            basic_block_expected.nxt_block_list[nxt_block_num].end_line,
                        ],
                    ):
                        return False
            else:
                # only assert the name that is converted to set
                real_names = {b.name for b in basic_block_real.nxt_block_list}
                expected_names = {b.name for b in basic_block_expected.nxt_block_list}
                assert real_names == expected_names

        return True

    def is_start_end(self, real_block, expected_block):
        if real_block[0] != expected_block[0]:
            return False
        elif real_block[1] != expected_block[1]:
            return False
        return True

    def assertBasicBlockListEqual(self, block_real_list, block_expected_list, name_required=True, preserve_seq=True):
        total_len = len(block_expected_list)
        assert_links = True
        for block_num, block_expected in enumerate(block_expected_list):
            try:
                for block_real in block_real_list:
                    if block_num == total_len - 1:
                        assert_links = False
                    # stop assert nxt_block_list if the current block is the last (selective testing)
                    if self.is_basic_block_equal(
                        block_real, block_expected, name_required, assert_links, preserve_seq=preserve_seq
                    ):
                        raise AssertTrueBasicBlock
            except AssertTrueBasicBlock:
                continue
            assert False, "Two basic blocks are not equal at num {}".format(block_num)

    def remove_block(self, blk):
        if len(blk.nxt_block_list) == 0:
            for prev in blk.prev_block_list:
                prev.nxt_block_list.remove(blk)
        elif len(blk.prev_block_list) == 0:
            for nxt in blk.nxt_block_list:
                nxt.prev_block_list.remove(blk)
        for prev, nxt in itertools.product(blk.prev_block_list, blk.nxt_block_list):
            prev.nxt_block_list.remove(blk)
            nxt.prev_block_list.remove(blk)
            Cfg.connect_2_blocks(prev, nxt)

    def assertStartEnd(self, real_block, expected_block, block_index, nxt_or_prev=""):
        assert real_block[0] == expected_block[0], "On block {}, the start line is not the same at {}".format(
            block_index, nxt_or_prev
        )
        assert real_block[1] == expected_block[1], "On block {}, the end line is not the same at {}".format(
            block_index, nxt_or_prev
        )
