from A4_CFG.var_ast import VarAst
from Common.cfg_common import remove_block_from_list, get_ast_node
from A3_LVN.Version2.ssa import SsaCode, SsaVariable, PhiFunction, Ssa
from .prologue import AdditionalStmt
from Common import cfg_common as CfgCommon
import copy


class BlockList(list):
    def get_block(self, block_to_find):
        for block in self.__iter__():
            if CfgCommon.is_blocks_same(block, block_to_find):
                return block

    def get_block_by_name(self, name):
        for block in self.__iter__():
            if block.name == name:
                return block

    def get_next_block_in_other_tree(self, block_to_find, other_tree):
        """
        yield the next block in a specific tree that found in this block list
        :param block_to_find: the RawBasicBlock to find
        :param other_tree: other tree
        :return: RawBasicBlock found in this list (not other tree)
        """
        for dom_succ_block in (CfgCommon.find_node(other_tree.dominator_nodes, block_to_find)).nxt_block_list:
            succ_block = CfgCommon.find_node(self, dom_succ_block)
            yield succ_block


class RawBasicBlock:
    BLOCK_IF = 0
    BLOCK_WHILE = 1

    IS_TRUE_BLOCK = 0
    IS_FALSE_BLOCK = 1

    def __init__(self, start_line=None, end_line=None, block_end_type=None, name=None):
        if not (isinstance(start_line, int) or not isinstance(end_line, int))\
                and start_line is not None and end_line is not None:
            raise TypeError
        self.name = name
        self._start_line = start_line
        self._end_line = end_line
        self._block_end_type = block_end_type
        self.nxt_block_list = []
        self.prev_block_list = []
        self.dominates_list = []
        self.df = []
        self.var_kill = set()
        self.ue_var = set()
        self.live_out = set()
        self.phi = set()
        self.ssa_code = SsaCode()

    @property
    def start_line(self):
        return self._start_line
        
    @start_line.setter
    def start_line(self, start_line):
        if not isinstance(start_line, int):
            raise TypeError
        self._start_line = start_line

    @property
    def end_line(self):
        return self._end_line

    @end_line.setter
    def end_line(self, end_line):
        if not isinstance(end_line, int):
            raise TypeError
        self._end_line = end_line

    @property
    def block_end_type(self):
        return self._block_end_type

    @block_end_type.setter
    def block_end_type(self, block_end_type):
        self._block_end_type = block_end_type

    def __repr__(self):
        s = "Block {} from line {} to {}".format(self.name, self.start_line, self.end_line)
        return s

    def get_num_of_parents(self):
        return len(self.prev_block_list)

    def insert_phi(self, var):
        self.phi.add(var)

    def has_phi(self, var):
        return var in self.phi

    def recompute_liveout(self):
        """
        recompute the liveout of this block
        :return: True if changed, False if not changed
        """
        new_liveout = set()
        for nxt_block in self.nxt_block_list:
            new_liveout.update(nxt_block.ue_var)
            new_liveout.update(nxt_block.live_out-(nxt_block.live_out & nxt_block.var_kill))
        if len(new_liveout - self.live_out) == 0:
            return False
        self.live_out = new_liveout
        return True

    def fill_phi(self):
        for phi_var in self.phi:
            existing_phi = self.ssa_code.get_phi_function(phi_var)
            if existing_phi is not None:
                existing_phi.fill_param(SsaVariable(phi_var, self.ssa_code.get_version(phi_var)))
            else:
                new_phi = PhiFunction(phi_var)
                new_phi.fill_param(SsaVariable(phi_var, self.ssa_code.get_version(phi_var)))
                self.ssa_code.code_list.insert(0, new_phi)


class FunctionLabel(RawBasicBlock):
    def __init__(self, start_line=None, end_line=None, name=None, args=list()):
        super(FunctionLabel, self).__init__(start_line=start_line, end_line=end_line, block_end_type='FunctionDef',
                                            name=name)
        self.func_tail = None
        self.args = args


class Cfg:
    def __init__(self, as_tree=None, *basic_block_args):
        self.__else_flag__ = False
        self.block_list = BlockList()
        self.dominator_tree = DominatorTree()
        self.globals_var = set()
        self.block_set = {}

        if as_tree is not None:
            self.as_tree = as_tree
            self.root, _ = self.parse(as_tree.body)

        if len(basic_block_args) != 0:
            for basic_block in basic_block_args:
                self.add_basic_block(basic_block)

    def add_basic_block(self, basic_block):
        if basic_block.start_line is not None:
            self.block_list.append(basic_block)

    def link_tail_to_cur_block(self, all_tail_list, basic_block):
        for tail in all_tail_list:
            self.connect_2_blocks(tail, basic_block)

    def build_if_body(self, if_block):
        all_tail_list = []
        ast_if_node = get_ast_node(self.as_tree, if_block.end_line)
        head_returned, tail_list = self.parse(ast_if_node.body)

        self.connect_2_blocks(if_block, head_returned)
        all_tail_list.extend(tail_list)

        head_returned, tail_list = self.parse(ast_if_node.orelse)
        if head_returned is not None:
            # has an else or elif
            self.connect_2_blocks(if_block, head_returned)
            all_tail_list.extend(tail_list)
        else:
            # no else
            # link this to the next statement
            all_tail_list.append(if_block)

        return all_tail_list

    def build_functiondef_body(self, func_block):
        ast_functiondef_node = get_ast_node(self.as_tree, func_block.end_line)
        head_returned, tail_list = self.parse(ast_functiondef_node.body)
        self.connect_2_blocks(func_block, head_returned)
        func_block.func_tail = tail_list

    def build_while_body(self, while_block):
        all_tail_list = []
        ast_while_node = get_ast_node(self.as_tree, while_block.end_line)
        head_returned, tail_list = self.parse(ast_while_node.body)

        self.connect_2_blocks(while_block, head_returned)
        self.link_tail_to_cur_block(tail_list, while_block)
        all_tail_list.append(while_block)
        return all_tail_list

    def build_call_body(self, basic_block):
        expr_node = get_ast_node(self.as_tree, basic_block.end_line)
        func_block = self.block_list.get_block_by_name(expr_node.value.func.id)

        # prologue
        add_stmt = AdditionalStmt(func_block, expr_node.value)
        backup_and_setup_stmt_list = add_stmt.get_backup_and_setup_stmt()
        prologue_block = RawBasicBlock(start_line=basic_block.end_line, end_line=basic_block.end_line,
                                       block_end_type='Prologue', name=f"prologue_L{basic_block.end_line}")
        prologue_block.ssa_code.code_list.extend(backup_and_setup_stmt_list)
        self.add_basic_block(prologue_block)
        self.connect_2_blocks(basic_block, prologue_block)
        self.connect_2_blocks(prologue_block, func_block)

        # epilogue
        epilogue_block = RawBasicBlock(start_line=basic_block.end_line, end_line=basic_block.end_line,
                                       block_end_type='Epilogue', name=f"epilogue_L{basic_block.end_line}")
        self.add_basic_block(epilogue_block)
        for tail in func_block.func_tail:
            self.connect_2_blocks(tail, epilogue_block)
        epilogue_block.ssa_code.code_list.extend(add_stmt.get_restore_backup_stmt())
        return [epilogue_block]

    def process_head_tail(self, head, current_block, all_tail_list):
        """
        assign the head if no tail, and link tail to current block
        :param head: the current head
        :param current_block: the current block that being processed
        :param all_tail_list: a list of blocks that are tails
        :return: the new head
        """
        if len(all_tail_list) == 0:
            return current_block
        else:
            self.link_tail_to_cur_block(all_tail_list, current_block)
            all_tail_list[:] = []
            return head

    def parse(self, ast_body):
        head = None
        all_tail_list = []
        if len(ast_body) == 0:
            return head, all_tail_list
        basic_block_parser = GetBlocks(self.as_tree, ast_body)
        for basic_block in basic_block_parser.get_basic_block():

            self.add_basic_block(basic_block)

            if basic_block.block_end_type == 'If':
                tail_list = self.build_if_body(basic_block)
                head = self.process_head_tail(head, basic_block, all_tail_list)
                all_tail_list.extend(tail_list)

            elif basic_block.block_end_type == 'While':
                while_block = self.separate_while_block(basic_block)

                tail_list = self.build_while_body(while_block)
                head = self.process_head_tail(head, basic_block, all_tail_list)
                all_tail_list.extend(tail_list)

            elif basic_block.block_end_type == 'FunctionDef':
                self.build_functiondef_body(basic_block)

            elif basic_block.block_end_type == 'Call':
                head = self.process_head_tail(head, basic_block, all_tail_list)
                tail_list = self.build_call_body(basic_block)
                all_tail_list.extend(tail_list)
            else:
                head = self.process_head_tail(head, basic_block, all_tail_list)
                all_tail_list.append(basic_block)

        return head, all_tail_list

    def separate_block(self, basic_block):
        separated_block = RawBasicBlock(basic_block.end_line, basic_block.end_line)
        basic_block.end_line -= 1
        self.connect_2_blocks(basic_block, separated_block)
        return separated_block

    def separate_while_block(self, basic_block):
        while_block = self.separate_block(basic_block)

        while_block.block_end_type = 'While'
        while_block.name = f"L{while_block.start_line}"
        basic_block.block_end_type = None
        self.add_basic_block(while_block)
        return while_block

    @staticmethod
    def connect_2_blocks(block1, block2):
        """
        connect block 1 to block 2
        :param block1:
        :param block2:
        :return:
        """
        block1.nxt_block_list.append(block2)
        block2.prev_block_list.append(block1)
    
    def fill_df(self):
        self.dominator_tree.build_dominance_frontier(self.root, self.block_list)

    def get_var_ast(self, block):
        for i in range(block.start_line, block.end_line + 1):
            ast_stmt = get_ast_node(self.as_tree, i)
            var_ast = VarAst(ast_stmt)
            yield var_ast.targets_var, var_ast.values_var

    def gather_initial_info(self):
        for block in self.block_list:
            for targets, values in self.get_var_ast(block):
                for value in values:
                    if value not in block.var_kill:
                        block.ue_var.add(value)
                        self.globals_var.add(value)
                block.var_kill |= set(targets)
                for target in targets:
                    if self.block_set.get(target) is None:
                        self.block_set[target] = [block]
                    else:
                        if block not in self.block_set[target]:
                            self.block_set[target].append(block)

    def compute_live_out(self):
        changed_flag = True
        while changed_flag:
            changed_flag = False
            for blocks in self.block_list:
                if blocks.recompute_liveout():
                    changed_flag = True

    def print_live_variable(self):
        for block in self.block_list:
            print(f"block {block.name}: UEVAR: {block.ue_var}, VARKILL : {block.var_kill}, LIVEOUT : {block.live_out}")

    def ins_phi_function_semi_pruned(self):
        for var in self.globals_var:
            worklist = copy.copy(self.block_set.get(var))
            if worklist is not None:
                for block in worklist:
                    for df_block in block.df:
                        if not df_block.has_phi(var):
                            df_block.insert_phi(var)
                            worklist.append(df_block)

    def ins_phi_function_pruned(self):
        no_phi_block = NoPhiDict()
        for var in self.globals_var:
            worklist = copy.copy(self.block_set.get(var))
            if worklist is not None:
                for block in worklist:
                    for df_block in block.df:
                        if not df_block.has_phi(var) and not no_phi_block.is_contain_var_no_phi_block(var, df_block):
                            if self.need_phi(var, df_block):
                                df_block.insert_phi(var)
                            else:
                                no_phi_block.ins_no_phi_block(var, df_block)
                            worklist.append(df_block)

    @staticmethod
    def need_phi(var, block):
        if var not in block.ue_var:
            if var in block.var_kill:
                    return False
            else:
                if var in block.live_out:
                    return True
                else:
                    return False
        else:
            return True

    def rename_to_ssa(self):
        for block in self.block_list:
            block.ssa_code.code_list = []
        self._rename_to_ssa(dict(), dict(), self.root)

    def _rename_to_ssa(self, counter_dict, stack_dict, block):
        block.ssa_code.reload_stack_and_counter(stack_dict, counter_dict)

        for phi_func in block.ssa_code.get_all_phi_functions():
            phi_func.target = SsaVariable(phi_func.var, block.ssa_code.update_version(phi_func.var))

        for i in range(block.start_line, block.end_line + 1):
            ast_node = get_ast_node(self.as_tree, i)
            block.ssa_code.add_ast_node_ssa(ast_node)

        for cfg_succ_block in block.nxt_block_list:
            cfg_succ_block.ssa_code.reload_stack_and_counter(stack_dict, counter_dict)
            cfg_succ_block.fill_phi()

        for dom_succ_block in (CfgCommon.find_node(self.dominator_tree.dominator_nodes, block)).nxt_block_list:
            self._rename_to_ssa(counter_dict, stack_dict, CfgCommon.find_node(self.block_list, dom_succ_block))

        for operation in block.ssa_code.code_list:
            if operation.target is not None:
                (stack_dict[operation.target.var]).remove(operation.target.version_num)


class GetBlocks:
    def __init__(self, as_tree, ast_node):
        self.as_tree = as_tree
        self.ast_node = ast_node
        self.start_line = None
        self.end_line = None

    def visit(self, ast_node):
        method = 'visit_' + ast_node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(ast_node)

    def get_basic_block(self):
        """
        yield all simple block in the ast, non recursively
        :return: yield all simple block
        """
        for ast_node in self.ast_node:
            # someone has to be the starting line
            if self.start_line is None:
                self.start_line = ast_node.lineno

            basic_block_list = self.visit(ast_node)

            if basic_block_list is not None:
                for block in basic_block_list:
                    yield block
                    self.start_line = None

        if self.start_line is not None:
            basic_block = RawBasicBlock(start_line=self.start_line, end_line=self.end_line)
            basic_block.ssa_code.add_ast_node_by_line_number(self.as_tree, self.start_line, ast_node.lineno)
            basic_block.name = 'L' + str(basic_block.start_line)
            yield basic_block

    def visit_If(self, ast_node):
        return self.visit_conditional_stmt(ast_node)

    def visit_While(self, ast_node):
        return self.visit_conditional_stmt(ast_node)

    def visit_conditional_stmt(self, ast_node):
        basic_block = RawBasicBlock(start_line=self.start_line, end_line=ast_node.lineno)
        basic_block.ssa_code.add_ast_node_by_line_number(self.as_tree, self.start_line, ast_node.lineno)
        basic_block.block_end_type = ast_node.__class__.__name__
        basic_block.name = 'L' + str(basic_block.start_line)
        return [basic_block]

    def visit_FunctionDef(self, ast_node):
        block_list_generated = []
        if self.start_line is not None and self.start_line != ast_node.lineno:
            basic_block = RawBasicBlock(start_line=self.start_line, end_line=self.end_line)
            basic_block.ssa_code.add_ast_node_by_line_number(self.as_tree, self.start_line, ast_node.lineno)
            basic_block.name = 'L' + str(basic_block.start_line)
            block_list_generated.append(basic_block)

        # yield the function label
        basic_block = FunctionLabel(start_line=ast_node.lineno, end_line=ast_node.lineno, name=ast_node.name,
                                    args=ast_node.args.args)
        block_list_generated.append(basic_block)
        return block_list_generated

    def visit_Assign(self, ast_node):
        self.end_line = ast_node.lineno
        return None

    def generic_visit(self, ast_node):
        self.end_line = ast_node.lineno
        return None

    def visit_Expr(self, ast_node):
        return self.visit(ast_node.value)

    def visit_Call(self, ast_node):
        basic_block = RawBasicBlock(start_line=self.start_line, end_line=ast_node.lineno,
                                    block_end_type=ast_node.__class__.__name__,
                                    name=f"L{str(self.start_line)}")
        basic_block.ssa_code.add_ast_node_by_line_number(self.as_tree, self.start_line, ast_node.lineno)
        return [basic_block]

    def visit_Return(self, ast_node):
        basic_block = RawBasicBlock(start_line=self.start_line, end_line=ast_node.lineno,
                                    block_end_type=ast_node.__class__.__name__,
                                    name=f"L{self.start_line}")

        # add all stmt before return
        basic_block.ssa_code.add_ast_node_by_line_number(self.as_tree, self.start_line, ast_node.lineno -1)
        # change return xxx to ret_val = xxx
        params = VarAst(ast_node)
        left_var = params.left_operand if params.left_operand is not None else None
        right_var = params.right_operand if params.right_operand is not None else None

        ret_stmt = Ssa(target='ret_val', left=left_var, op=params.body_op, right=right_var)
        basic_block.ssa_code.code_list.append(ret_stmt)
        return [basic_block]


class NoPhiDict(dict):
    def ins_no_phi_block(self, var, block):
        if self.get(var) is None:
            self.__setitem__(var, [block])
        else:
            self.get(var).append(block)

    def is_contain_var_no_phi_block(self, var, block):
        if self.get(var) is None:
            return False
        else:
            return block in self.get(var)


class DominatorTree:
    def __init__(self, cfg=None):
        self.dominator_root = None
        self.dominator_nodes = BlockList()
        if cfg is not None:
            self.cfg = cfg

    def build_dominance_frontier(self, root, block_list):
        self.fill_dominates(root, block_list)
        self.build_tree(root)
        self.fill_df(block_list)

    def fill_dominates(self, cfg_root, block_list):
        """
        find and fill the dominance relationship of all the blocks
        :param cfg_root: the root for the block
        :param block_list: the list of all blocks
        :return: None
        """
        for removed_block_num in (range(len(block_list))):
            dom_root = copy.deepcopy(cfg_root)
            dom_block_list = copy.copy(block_list)
            # remove the block
            # walk again
            dom_root = CfgCommon.delete_node(dom_root, block_list[removed_block_num])

            for not_dom_block in CfgCommon.walk_block(dom_root):
                remove_block_from_list(dom_block_list, not_dom_block)

            remove_block_from_list(dom_block_list, block_list[removed_block_num])
            block_list[removed_block_num].dominates_list.extend(dom_block_list)
            del dom_root

    def build_tree(self, root):
        # TODO: clarify the code below
        for block_in_cfg in CfgCommon.walk_block(root):
            block_in_dom_list = RawBasicBlock(block_in_cfg.start_line, block_in_cfg.end_line)
            self.dominator_nodes.append(block_in_dom_list)
            for dom_block in block_in_cfg.dominates_list:
                dom_block_in_dom_list = self.dominator_nodes.get_block(dom_block)
                if not dom_block_in_dom_list.prev_block_list:
                    Cfg.connect_2_blocks(block_in_dom_list, dom_block_in_dom_list)

        self.dominator_root = self.dominator_nodes[-1]

    def fill_df(self, block_list):
        for nodes in block_list:
            if nodes.get_num_of_parents() > 1:
                for pred_node in nodes.prev_block_list:
                    runner = pred_node
                    while not CfgCommon.is_blocks_same(self.dominator_nodes.get_block(runner),
                                                        self.get_idom(block_list, nodes)) \
                            and runner is not None:
                        runner.df.append(nodes)
                        runner = self.get_idom(block_list, runner)

    def get_idom(self, block_list, cfg_node):
        dom_node = self.dominator_nodes.get_block(cfg_node)
        if dom_node.prev_block_list:
            cfg_idom_node = CfgCommon.find_node(block_list, dom_node.prev_block_list[0])
            return cfg_idom_node
        return None


def build_blocks(*args, block_links):
    block_list = []
    for i in range(len(args)):
        basic_block = RawBasicBlock(args[i][0], args[i][1], args[i][2])

        block_list.append(basic_block)

    if block_links is not None:
        for i in range(len(block_links)):
            nxt_block_list = block_links.get(str(i))
            for nxt_block_num in nxt_block_list:
                Cfg.connect_2_blocks(block_list[i], block_list[nxt_block_num])

    return block_list
