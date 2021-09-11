import copy
from collections import deque
from typing import Dict, List, Tuple

import klara.common.common as common
from klara.common.cfg_common import find_blocks_involved

from . import exceptions, manager, nodes, utilities
from .decorators import deprecated
from .ssa import AttributeEnumerator, SsaCode
from .ssa_visitors import AstAttrSeparator, VariableGetter
from .use_def_chain import link_stmts_to_def

MANAGER = manager.AstManager()
TEMP_ASSIGN = "TempAssign"
ineq_solver = utilities.make_import_optional(".ineq_solver", "klara.core", manager=MANAGER)


class BlockList(list):
    def get_block_by_name(self, name):
        # type: (str) -> RawBasicBlock
        if type(name) is str:
            for block in self.__iter__():
                if block.name == name:
                    return block


class RawBasicBlock(object):
    BLOCK_IF = 0
    BLOCK_WHILE = 1

    IS_TRUE_BLOCK = 0
    IS_FALSE_BLOCK = 1

    def __init__(
        self,
        start_line=None,
        end_line=None,
        block_end_type="",
        name=None,
        parent_node=None,
        scope=None,
        block_end_code=None,
    ):
        if (
            not (isinstance(start_line, int) or not isinstance(end_line, int))
            and start_line is not None
            and end_line is not None
        ):
            raise TypeError
        self.name = name
        self.start_line = start_line
        self.end_line = end_line
        self.block_end_type = block_end_type
        # the ast code that associate with the block_end_type
        self.block_end_code = block_end_code
        self.nxt_block_list = []
        self.prev_block_list = []
        self.rev_dom_list = set()
        # the forward link in the dominator tree
        self.idom = []
        # the immediate parent in the dominator tree
        self.rev_idom = None
        self.df = []
        self.var_kill = set()
        self.ue_var = set()
        self.live_out = set()
        self.phi = set()
        # phi(s) string representation to check the availability of self.phi.
        # this is needed since self.phi is using the node instead of string,
        # and we don't want duplicate.
        self._phi_repr = set()
        self.ssa_code = SsaCode()
        self.parent_node = parent_node
        # a duplicate of the containing node's scope()
        self.scope = scope
        # a set of conditions ast statement that is True to reach this point.
        self.conditions = set()
        # dictionary containing value require to reach this block
        self.cond_requirements = None
        # condition cache for prompt
        self.cond_prompt_cache = {}

    @classmethod
    def from_list(cls, lst, **kwargs):
        start_line = lst[0].lineno
        end_line = lst[-1].lineno
        c = cls(start_line=start_line, end_line=end_line, block_end_code=lst[-1])
        for code in lst:
            c.ssa_code.add_code(code, c)
        for attr, value in kwargs.items():
            setattr(c, attr, value)
        return c

    def __repr__(self):
        s = "Block {} from line {} to {}".format(self.name, self.start_line, self.end_line)
        return s

    def insert_doms(self, dom_blks):
        """insert dom_blk such that dom_blks is dominating self"""
        subtracted_blk = self.rev_dom_list - dom_blks
        self.rev_dom_list = dom_blks

    def get_num_of_parents(self):
        return len(self.prev_block_list)

    def insert_phi(self, var):
        """Insert into phi variables if it does not exist"""
        self._phi_repr.add(str(var))
        self.phi.add(var)

    def has_phi(self, var):
        return str(var) in self._phi_repr

    def recompute_liveout(self):
        """
        recompute the liveout of this block
        :return: True if changed, False if not changed
        """
        new_liveout = set()
        for nxt_block in self.nxt_block_list:
            new_liveout.update(nxt_block.ue_var)
            calculated_lo = nxt_block.live_out - (nxt_block.live_out & nxt_block.var_kill)
            new_liveout.update(calculated_lo)
            MANAGER.logger.debug("SSA", "updating new liveout for block: ({}) --> {}", nxt_block, calculated_lo)
        if len(new_liveout - self.live_out) == 0:
            return False
        self.live_out = new_liveout
        return True

    def fill_phi(self):
        for phi_var in self.phi:
            existing_phi = self.ssa_code.get_phi_function(phi_var)
            if existing_phi:
                # check if current variable already existed.
                cls = nodes.Name if isinstance(phi_var, nodes.AssignName) else nodes.Attribute
                phi_ssa_var = cls.quick_build_from_counter_part(phi_var)
                phi_ssa_var.convert_to_ssa()
                phi_ssa_var.parent = existing_phi
                if not existing_phi.value.check_exist(phi_ssa_var.version):
                    MANAGER.logger.debug(
                        "SSA",
                        """\
                         creating a new Phi variable {} for statement in lineno: {}
                         """,
                        phi_ssa_var,
                        existing_phi.lineno,
                    )
                    existing_phi.value.value.append(phi_ssa_var)
            else:
                self.ssa_code.add_phi_function(phi_var, self.scope.ast_node, self)

    def enumerate(self, _=None):
        for ast_stmt in self.get_code_to_analyse():
            # MANAGER.logger.debug("SSA", "Enumerating stmt: '{}' to SSA form", ast_stmt)
            AttributeEnumerator.enumerate(ast_stmt, False, False)

    def cleanup_code(self):
        """
        remove all target from var_version_list (stack). Typically used in renaming when back up of node happen.
        :return: None
        """
        for operation in self.get_code_to_analyse():
            var_getter = VariableGetter.get_variable(operation)
            self.ssa_code.remove_targets_from_var_stack(var_getter.targets)

    def get_code_to_analyse(self):
        # use to prevent analysing code in ParentScopeBlock
        for code in self.ssa_code.code_list:
            yield code

    def get_phi_functions(self):
        for code in self.get_code_to_analyse():
            if code.statement().is_phi is True:
                yield code

    def rename(self):
        queue = deque()
        queue.append(self)
        analyzed_block = set()
        while len(queue) > 0:
            blk = queue[0]
            if blk in analyzed_block:
                # when meet the second time, also means that the subsequent block has already analyzed
                blk.cleanup_code()
                queue.remove(blk)
                continue
            analyzed_block.add(blk)
            if isinstance(blk, ParentScopeBlock) and blk != self:
                blk.rename()
            blk.enumerate()
            for cfg_succ_block in blk.nxt_block_list:
                cfg_succ_block.fill_phi()
                for phi_stmt in cfg_succ_block.get_phi_functions():
                    link_stmts_to_def(phi_stmt, allow_uninitialized=True, target_phi=True)
            # reversed the idom insertion since the sequence is important. The higher level node
            # will be rename first.
            queue.extendleft(reversed(blk.idom))

    def get_conditions_from_prev(self) -> set:
        """Return the conditions from the immediate predecessor.
            A
           / \
          B   C
        Calling this method on block B will return the condition to enter B from A.
        Return a sets of condition.
        """
        results = set()
        for prev in self.prev_block_list:
            try:
                if len(prev.nxt_block_list) == 2:
                    if prev.nxt_block_list.index(self) == 0:
                        results.add(prev.ssa_code.code_list[-1])
                    else:
                        results.add(prev.ssa_code.code_list[-1].invert_condition())
            except AttributeError:
                # condition is not an valid expr
                continue
        return results


class ParentScopeBlock(RawBasicBlock):
    """
    Block that defined another scope within. E.g,
    def foo():  ---> ParentScopeBlock
        x = 1   ---> RawBasicBlock
    """

    def __init__(
        self,
        start_line=None,
        end_line=None,
        name=None,
        block_end_type=None,
        stack_dict=None,
        counter_dict=None,
        scope_name="",
        parent_node=None,
        ast_node=None,
    ):
        super(ParentScopeBlock, self).__init__(
            start_line=start_line, end_line=end_line, block_end_type=block_end_type, name=name, parent_node=parent_node
        )
        self.locals = dict()
        self.var_version_list = stack_dict if stack_dict else dict()
        self.counter = counter_dict if counter_dict else dict()
        self.scope_name = scope_name
        self.blocks = BlockList()
        self.phi_stub_block = None
        # ast node that this block wrapped
        self.ast_node = ast_node
        self.ssa_code.add_code(ast_node, self)

    def get_code_to_analyse(self):
        # use to prevent analysing code in ParentScopeBlock
        yield from ()

    def enumerate(self, cfg_instance=None):
        # enumerate the containing scope as well
        assert len(self.ssa_code.code_list) <= 1, "must only contain 0 or 1 node"
        super(ParentScopeBlock, self).enumerate(cfg_instance)

    def fill_dominates(self):
        """solving the data flow equations
        Dom(n) = {n} | (&=Dom(m)) where m = preds(n)
        """
        MANAGER.logger.debug("CFG", "fill dominates of block: {}", self)
        all_set = set(self.blocks)
        all_set.add(self)
        for blk in self.blocks:
            blk.insert_doms(all_set)
        self.rev_dom_list = {self}
        changed = True
        while changed:
            changed = False
            for blk in self.blocks:
                if len(blk.prev_block_list) > 0:
                    preds_dom = set.intersection(*(prev.rev_dom_list for prev in blk.prev_block_list))
                else:
                    preds_dom = set()
                preds_dom.add(blk)
                if blk.rev_dom_list != preds_dom:
                    blk.insert_doms(preds_dom)
                    changed = True
        if self.ast_node:
            for scope in self.ast_node.containing_scope:
                if scope.refer_to_block:
                    scope.refer_to_block.fill_dominates()

    def fill_idom(self):
        """fill `idom` and `rev_idom` of all blocks.
        This essentially build the dominator tree.
        """

        def _find_idom(b, rev_doms):
            queue = deque()
            queue.append(b)
            while len(queue) > 0:
                block = queue.pop()
                _visited.append(block)
                for prev_blk in block.prev_block_list:
                    if prev_blk != blk and prev_blk not in _visited:
                        if prev_blk in rev_doms:
                            return prev_blk
                        else:
                            queue.appendleft(prev_blk)
                    else:
                        continue
            return None

        for blk in self.blocks:
            _visited = []
            idom_blk = _find_idom(blk, blk.rev_dom_list)
            blk.rev_idom = idom_blk
            if idom_blk:
                idom_blk.idom.append(blk)
                MANAGER.logger.debug("CFG", "make block {}'s idom to point at {}", idom_blk, blk)
        if self.ast_node:
            for scope in self.ast_node.containing_scope:
                if scope.refer_to_block:
                    scope.refer_to_block.fill_idom()

    def fill_df(self, block_list):
        block_list = find_blocks_involved(self, block_list)
        for nd in block_list:
            if nd.get_num_of_parents() > 1:
                for pred_node in nd.prev_block_list:
                    runner = pred_node
                    if runner in block_list:
                        while runner is not None and runner != nd.rev_idom:
                            runner.df.append(nd)
                            MANAGER.logger.debug("CFG", "applying dominance frontier of block: {} to {}", runner, nd)
                            runner = runner.rev_idom
        if self.ast_node:
            for scope in self.ast_node.containing_scope:
                if scope.refer_to_block:
                    scope.refer_to_block.fill_df(scope.refer_to_block.blocks)

    def rename(self):
        if self.ast_node:
            if isinstance(self.ast_node, nodes.ClassDef):
                super(ParentScopeBlock, self).rename()
            for scope in self.ast_node.containing_scope:
                if isinstance(scope, (nodes.FunctionDef, nodes.Lambda)):
                    scope.init_class_methods()
                if isinstance(scope, nodes.Lambda):
                    # an ugly hack to force to recurse the body of lambda
                    # for nested labda statement
                    block = LambdaLabel(scope)
                    scope.refer_to_block = block
                if scope.refer_to_block:
                    scope.refer_to_block.rename()
            if not isinstance(self.ast_node, nodes.ClassDef):
                super(ParentScopeBlock, self).rename()

    def fill_conditions(self):
        """Fill all the block with a list of conditions to reach.
        Solve for backward simple data flow equation:
        cond(n) = (&=cond(m)) | split_edge(m)
        where m is pred(n)

        !. Gather all prev into a list.
        2. Cancel all get_conditions_from_prev() from the list and record whatever left.
        3. Intersect the list and add with the leftover.
        """
        changed = True
        while changed:
            changed = False
            for blk in self.blocks:
                if len(blk.prev_block_list) > 0:
                    conditions = set.union(*(prev.conditions for prev in blk.prev_block_list))
                    intersected_conditions = set.intersection(*(prev.conditions for prev in blk.prev_block_list))
                else:
                    conditions = intersected_conditions = set()
                valid_condition = blk.get_conditions_from_prev()
                valid_condition = utilities.is_subset(valid_condition, conditions)
                conditions = intersected_conditions | valid_condition
                if blk.conditions != conditions:
                    blk.conditions = conditions
                    changed = True

        if self.ast_node:
            for scope in self.ast_node.containing_scope:
                if scope.refer_to_block:
                    scope.refer_to_block.fill_conditions()

    def apply_transform(self):
        for block in self.blocks:
            for code in block.get_code_to_analyse():
                MANAGER.apply_transform(code)
            for cond in block.conditions:
                MANAGER.apply_transform(cond)

        if self.ast_node:
            for scope in self.ast_node.containing_scope:
                if scope.refer_to_block:
                    scope.refer_to_block.apply_transform()


class FunctionLabel(ParentScopeBlock):
    def __init__(
        self, start_line=None, end_line=None, name=None, args=None, func_name="", parent_node=None, function_node=None
    ):
        super(FunctionLabel, self).__init__(
            start_line=start_line,
            end_line=end_line,
            block_end_type="FunctionDef",
            name=name,
            scope_name=func_name,
            parent_node=parent_node,
            ast_node=function_node,
        )
        self.func_tail = []  # blocks that contains return stmt or
        self.args = args

    @classmethod
    def from_node(cls, ast_node):
        return cls(
            start_line=ast_node.lineno,
            end_line=ast_node.lineno,
            name=ast_node.name,
            args=ast_node.args,
            func_name=ast_node.name,
            parent_node=ast_node.parent,
            function_node=ast_node,
        )


class LambdaLabel(ParentScopeBlock):
    """
    An empty block just to able to set up nested lambda
    """

    def __init__(self, lambda_node):
        super(LambdaLabel, self).__init__()
        self.ast_node = lambda_node


class ClassLabel(ParentScopeBlock):
    def __init__(
        self, start_line=None, end_line=None, name=None, args=None, class_name="", parent_node=None, class_node=None
    ):
        super(ClassLabel, self).__init__(
            start_line=start_line,
            end_line=end_line,
            block_end_type="ClassDef",
            name=name,
            scope_name=class_name,
            parent_node=parent_node,
            ast_node=class_node,
        )
        self.func_tail = []
        self.inherit = []  # type: List[ClassLabel]
        self.args = args

    @classmethod
    def from_node(cls, ast_node):
        return cls(
            start_line=ast_node.lineno,
            end_line=ast_node.lineno,
            name=ast_node.name,
            class_name=ast_node.name,
            parent_node=ast_node.parent,
            class_node=ast_node,
        )


class ModuleLabel(ParentScopeBlock):
    def __init__(self, name=None, parent_node=None, module_node=None):
        super(ModuleLabel, self).__init__(
            start_line=None,
            end_line=None,
            block_end_type="Module",
            name=name,
            parent_node=parent_node,
            ast_node=module_node,
        )
        self.path = ""


class PhiStubBlock(RawBasicBlock):
    """Block to force phi function at every scope, also forcing update var_version_list to latest"""

    def __init__(self, scope=None):
        super(PhiStubBlock, self).__init__(start_line=-1, end_line=-1, scope=scope, name="PhiStub")

    def __repr__(self):
        return "a phi stub block"


class TempAssignBlock(RawBasicBlock):
    """block for temporary assignment for FunctionDef/ClassDef for renaming purpose"""

    def __init__(self, *args, **kwargs):
        super(TempAssignBlock, self).__init__(*args, **kwargs, name=TEMP_ASSIGN, block_end_type=TEMP_ASSIGN)


class Cfg:
    def __init__(self, as_tree=None):
        self.__else_flag__ = False
        self.block_list = BlockList()
        self.globals_var = set()
        self.block_set: Dict[nodes.Variable, RawBasicBlock] = {}

        if as_tree is not None:
            self.as_tree = as_tree
            # add the entry block
            with MANAGER.logger.info("CFG", "parsing the ast..."):
                self.root, _, _ = self.parse(as_tree)

    def add_basic_block(self, basic_block):
        # Module block doesn't have line number
        if basic_block.start_line is not None or basic_block.block_end_type == "Module":
            if basic_block.block_end_type != "Module":
                basic_block.scope.blocks.append(basic_block)
            self.block_list.append(basic_block)

    def link_tail_to_cur_block(self, all_tail_list, basic_block):
        for tail in all_tail_list:
            self.connect_2_blocks(tail, basic_block)
        all_tail_list[:] = []

    def insert_force_phi_block(self, func_block, tail_list):
        phi_stub = PhiStubBlock(func_block)
        self.add_basic_block(phi_stub)
        for tail in tail_list:
            self.connect_2_blocks(tail, phi_stub)
        func_block.phi_stub_block = phi_stub

    def build(self, block, head, all_tail_list, func_tail_list):
        """will return head"""
        method_str = "build_" + block.block_end_type.lower()
        meth = getattr(self, method_str, self.build_generic)
        MANAGER.logger.debug("AST2CFG", "building '{}' block: {}", block.block_end_type, block)
        tail_list, func_tail = meth(block)
        if not isinstance(block.block_end_code, nodes.LocalsDictNode):
            head = head or block
            self.link_tail_to_cur_block(all_tail_list, block)
            all_tail_list.extend(tail_list)
            func_tail_list.extend(func_tail)
        return head

    def build_if(self, if_block):
        all_tail_list, func_tail_list = [], []
        ast_if_node = if_block.ssa_code.code_list[-1]
        if_block.ssa_code.code_list[-1] = ast_if_node.test  # replace the entire node with only the test expr
        head_returned, tail_list, func_tail = self.parse(ast_if_node.body)
        self.connect_2_blocks(if_block, head_returned)
        all_tail_list.extend(tail_list)
        func_tail_list.extend(func_tail)
        head_returned, tail_list, func_tail = self.parse(ast_if_node.orelse)
        if head_returned is not None:
            # has an else or elif
            self.connect_2_blocks(if_block, head_returned)
            all_tail_list.extend(tail_list)
            func_tail_list.extend(func_tail)
        else:
            # no else
            # link this to the next statement
            all_tail_list.append(if_block)
        return all_tail_list, func_tail_list

    def build_functiondef(self, func_block):
        # type: (FunctionLabel) -> Tuple[List, List]
        ast_functiondef_node = func_block.ssa_code.code_list[-1]
        head_returned, tail_list, func_tail_list = self.parse(ast_functiondef_node.body)
        self.connect_2_blocks(func_block, head_returned)
        func_block.func_tail.extend(func_tail_list)
        self.insert_force_phi_block(func_block, tail_list)
        return [], []

    def build_return(self, return_block):
        self.build_generic(return_block)
        return [], [return_block]

    def build_classdef(self, class_block):
        # type: (ClassLabel) -> Tuple[List, List]
        class_node = class_block.ssa_code.code_list[-1]
        head_returned, tail_list, func_tail_list = self.parse(class_node.body)
        if head_returned:
            # contain stmt in class (that is not functiondef)
            self.connect_2_blocks(class_block, head_returned)

        # tail_list should be func_tail_list at the end
        self.insert_force_phi_block(class_block, tail_list)
        return [], []

    def build_module(self, module_block):
        head_returned, tail_list, _ = self.parse(self.as_tree.body)
        self.connect_2_blocks(module_block, head_returned)
        self.insert_force_phi_block(module_block, tail_list)
        return [], []

    def build_while(self, while_block):
        while_block = self.separate_block(while_block, "While")
        ast_while_node = while_block.ssa_code.code_list[-1]
        while_block.ssa_code.code_list[-1] = ast_while_node.test
        head_returned, tail_list, func_tail = self.parse(ast_while_node.body)
        self.connect_2_blocks(while_block, head_returned)
        self.link_tail_to_cur_block(tail_list, while_block)
        return [while_block], func_tail

    def build_for(self, for_block):
        func_tails = []
        for_block = self.separate_block(for_block, "For")
        ast_for_node = for_block.ssa_code.code_list[-1]
        for_block.ssa_code.code_list[-1] = ast_for_node.generate_ssa_stmt()
        head_returned, tail_list, func_tail = self.parse(ast_for_node.body)
        func_tails.extend(func_tail)
        self.connect_2_blocks(for_block, head_returned)
        self.link_tail_to_cur_block(tail_list, for_block)
        head_returned, tail_list, func_tail = self.parse(ast_for_node.orelse)
        func_tails.extend(func_tail)
        self.connect_2_blocks(for_block, head_returned)
        return [for_block, head_returned], func_tail

    def build_call(self, basic_block):
        return [basic_block], []

    def build_generic(self, basic_block):
        return [basic_block], []

    def parse(self, ast_body):
        head = None
        all_tail_list, func_tail_list = [], []
        basic_block_parser = GetBlocks(self.as_tree, ast_body)
        for basic_block in basic_block_parser.get_basic_block():
            self.add_basic_block(basic_block)
            head = self.build(basic_block, head, all_tail_list, func_tail_list)

        return head, all_tail_list, func_tail_list

    def separate_block(self, basic_block, block_end_type=""):
        if basic_block.start_line == basic_block.end_line:
            # if blocks only contain 1 line of code, it's not needed to be separated
            return basic_block
        else:
            separated_block = RawBasicBlock(basic_block.end_line, basic_block.end_line)
            separated_block.ssa_code.code_list.append(basic_block.ssa_code.code_list[-1])
            separated_block.scope = basic_block.scope
            basic_block.ssa_code.code_list = basic_block.ssa_code.code_list[:-1]
            basic_block.end_line -= 1
            self.connect_2_blocks(basic_block, separated_block)
            separated_block.block_end_type = block_end_type
            separated_block.name = "L{}".format(separated_block.start_line)
            basic_block.block_end_type = ""
            self.add_basic_block(separated_block)
            return separated_block

    @staticmethod
    def connect_2_blocks(block1, block2):
        # type: (RawBasicBlock, RawBasicBlock) -> None
        """
        connect block 1 to block 2
        :param block1: block no.1
        :param block2: block no.2
        :return:
        """
        MANAGER.logger.debug("AST2CFG", "connecting block: {} to {}", block1, block2)
        if block1 is not None and block2 is not None:
            block1.nxt_block_list.append(block2)
            block2.prev_block_list.append(block1)

    def fill_df(self):
        with MANAGER.logger.info("SSA", "Calculating dominance frontier"):
            self.root.fill_dominates()
            self.root.fill_idom()
            self.root.fill_df(self.block_list)

    def gather_initial_info(self):
        with MANAGER.logger.info("SSA", "Gathering initial information"):
            for block in self.block_list:
                for stmt in block.get_code_to_analyse():
                    sep = AstAttrSeparator()
                    sep.visit(stmt)
                    for load_var in sep.load:
                        load_var = str(load_var)
                        if load_var not in block.var_kill:
                            block.ue_var.add(load_var)
                            self.globals_var.add(load_var)
                            MANAGER.logger.debug("SSA", "adding '{}' to the globals var", load_var)
                    for store_var in sep.store:
                        block.var_kill.add(str(store_var))
                        self.block_set[store_var] = block

    def compute_live_out(self):
        MANAGER.logger.info("SSA", "Computing Live-out of variables")
        changed_flag = True
        while changed_flag:
            changed_flag = False
            for blocks in self.block_list:
                if blocks.recompute_liveout():
                    changed_flag = True

    @deprecated
    def ins_phi_function_semi_pruned(self):
        for var in self.globals_var:
            worklist = copy.copy(self.block_set.get(var))
            if worklist is not None:
                for block in worklist:
                    for df_block in block.df:
                        if not df_block.has_phi(var):
                            df_block.insert_phi(var)
                            worklist.append(df_block)

    @deprecated
    def ins_phi_function_pruned(self):
        MANAGER.logger.info("SSA", "Inserting pruned phi function for all blocks.")

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

        no_phi_block = NoPhiDict()
        for var in self.globals_var:
            worklist = copy.copy(self.block_set.get(var))
            if worklist is not None:
                for block in worklist:
                    for df_block in block.df:
                        if not df_block.has_phi(var) and not no_phi_block.is_contain_var_no_phi_block(var, df_block):
                            if need_phi(var, df_block):
                                MANAGER.logger.debug("SSA", "insert '{}' as phi function for block: {}", var, df_block)
                                df_block.insert_phi(var)
                            else:
                                no_phi_block.ins_no_phi_block(var, df_block)
                            worklist.append(df_block)

    def ins_phi_function_all(self):
        with MANAGER.logger.info("SSA", "Inserting phi function for all blocks."):
            for var, set_block in self.block_set.items():
                worklist = deque((set_block,))
                while len(worklist) > 0:
                    block = worklist.pop()
                    for df_block in block.df:
                        if not df_block.has_phi(var):
                            MANAGER.logger.debug("SSA", "insert '{}' as phi function for block: {}", var, df_block)
                            df_block.insert_phi(var)
                            worklist.append(df_block)

    def rename_to_ssa(self):
        with MANAGER.logger.info("SSA", "Renaming variables using all the information gathered above."):
            self.root.rename()

    def convert_to_ssa(self):
        self.fill_df()
        self.gather_initial_info()
        self.ins_phi_function_all()
        self.rename_to_ssa()

    def apply_root_transform(self):
        # apply transform also to the generated statement.
        self.root.apply_transform()

    def apply_transform(self):
        MANAGER.logger.debug("INFER", "Applying transformation for all nodes")
        MANAGER.apply_transform(self.as_tree)
        self.apply_root_transform()

    def fill_all_conditions(self):
        with MANAGER.logger.info("SSA", "Filling all conditions in the cfg"):
            self.root.fill_conditions()


class GetBlocks(object):
    """look for stmt that define the block edge and partition accordingly
    e.g.
    x = 1
    if x:
        pass
    x = 3

    This will yield block [1, 2] and [4, 4], since 'If' node is multi line block ranging from 2 to 3
    """

    def __init__(self, as_tree, ast_node):
        self.as_tree = as_tree
        self.ast_node = ast_node
        self.start_line = None
        self.end_line = None
        self._cache = []
        self._cache_scope = None

    def flush(self, **kwargs):
        """create a RawBasicBlock from _cache, add attr to blk based on **kwargs"""
        if len(self._cache) > 0:
            kwargs["scope"] = self._cache_scope
            blk = RawBasicBlock.from_list(self._cache, **kwargs)
            blk.name = "L" + str(blk.start_line)
            self._cache = []
            self._cache_scope = None
            return blk

    def _append_cache(self, node):
        if len(self._cache) == 0 or self._cache[-1] != node:
            self._cache.append(node)
            if self._cache_scope is not None:
                if self._cache_scope != node.scope().refer_to_block:
                    raise exceptions.StructureError(
                        override_msg=common.ms(
                            """\
                        node: {} have scope: {}, which is different than cached scope: {}
                        """.format(
                                node, node.scope(), self._cache_scope
                            )
                        )
                    )
            else:
                self._cache_scope = node.scope().refer_to_block

    def visit(self, ast_node):
        method = "visit_" + ast_node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(ast_node)

    def generic_visit(self, ast_node):
        self._append_cache(ast_node.statement())
        self.end_line = ast_node.lineno
        return None

    def get_basic_block(self):
        """
        yield all simple block in the ast, non recursively
        :return: yield all simple block
        """
        if isinstance(self.ast_node, nodes.Module):
            yield from self.visit_Module(self.ast_node)
        else:
            for node in self.ast_node:
                # someone has to be the starting line
                if self.start_line is None:
                    self.start_line = node.lineno
                basic_block_list = self.visit(node)
                if basic_block_list is not None:
                    for block in basic_block_list:
                        MANAGER.logger.debug("AST2CFG", "separated block: {}", block)
                        yield block
                    self.start_line = None
            # yield the final block
            if len(self._cache) > 0:
                basic_block = self.flush()
                MANAGER.logger.debug(
                    "AST2CFG",
                    """Flush the final block of type {} from lineno {} to {}""",
                    basic_block.block_end_type,
                    basic_block.start_line,
                    basic_block.end_line,
                )
                yield basic_block

    def visit_Module(self, ast_node):
        module_block = ModuleLabel(name="Module", parent_node=ast_node.parent, module_node=ast_node)
        yield module_block

    def visit_If(self, ast_node):
        return self.visit_conditional_stmt(ast_node)

    def visit_While(self, ast_node):
        return self.visit_conditional_stmt(ast_node)

    def visit_For(self, ast_node):
        return self.visit_conditional_stmt(ast_node)

    def visit_conditional_stmt(self, ast_node):
        self._append_cache(ast_node.statement())
        basic_block = self.flush()
        basic_block.block_end_type = ast_node.__class__.__name__
        basic_block.name = "L" + str(basic_block.start_line)
        return [basic_block]

    def visit_FunctionDef(self, ast_node):
        block_list_generated = []
        block = self.flush()
        if block is None:
            # create a basic block to temporary hold the function assignment
            block = TempAssignBlock(ast_node.lineno, ast_node.lineno)
        block_list_generated.append(block)
        # to temporary fix issues #kng80
        for stmt in ast_node.generate_ssa_func():
            block.ssa_code.add_code(stmt, block)
        # add all the decorators name to be rename
        if len(ast_node.decorator_list) > 0:
            decorator_expr = ast_node.generate_ssa_decorator()
            block.ssa_code.add_code(decorator_expr, block)
        # yield the function label
        function_block = FunctionLabel.from_node(ast_node)
        function_block.block_end_code = ast_node
        block_list_generated.append(function_block)
        return block_list_generated

    def visit_Assign(self, ast_node):
        return self.visit(ast_node.value)

    def visit_Expr(self, ast_node):
        return self.visit(ast_node.value)

    def visit_Call(self, ast_node):
        self._append_cache(ast_node.statement())
        basic_block = self.flush(block_end_type=ast_node.__class__.__name__, parent_node=ast_node.parent)
        return [basic_block]

    def visit_Return(self, ast_node):
        # change return xxx to ret_val = xxx
        ret_stmt = ast_node.generate_ssa_stmt()
        self._append_cache(ret_stmt)
        basic_block = self.flush(block_end_type=ast_node.__class__.__name__, parent_node=ast_node.parent)
        # also point the block of original return stmt.
        ast_node.refer_to_block = basic_block
        return [basic_block]

    def visit_ClassDef(self, ast_node):
        block_list_generated = []
        block = self.flush()
        if block is None:
            # create a basic block to temporary hold the function assignment
            block = TempAssignBlock(ast_node.lineno, ast_node.lineno)
        # to temporary fix issues #kng80
        for stmt in ast_node.generate_ssa_func():
            block.ssa_code.add_code(stmt, block)
        block_list_generated.append(block)
        # yield class label
        class_block = ClassLabel.from_node(ast_node)
        class_block.block_end_code = ast_node
        block_list_generated.append(class_block)
        return block_list_generated


class NoPhiDict(dict):
    def ins_no_phi_block(self, var, block):
        if self.get(var) is None:
            self.__setitem__(var, [block])

    def is_contain_var_no_phi_block(self, var, block):
        if self.get(var) is None:
            return False
        else:
            return block in self.get(var)


def build_blocks(*args, **kwargs):
    block_links = kwargs.get("block_links")
    block_list = []
    for i in range(len(args)):
        name = args[i][3] if len(args[i]) > 3 else None
        basic_block = RawBasicBlock(args[i][0], args[i][1], args[i][2], name=name)
        block_list.append(basic_block)

    if block_links is not None:
        for i in range(len(block_links)):
            nxt_block_list = block_links.get(str(i))
            for nxt_block_num in nxt_block_list:
                Cfg.connect_2_blocks(block_list[i], block_list[nxt_block_num])

    return block_list
