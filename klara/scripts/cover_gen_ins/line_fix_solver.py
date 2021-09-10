import z3

from klara.core import cfg, nodes, utilities
from klara.core.ssa_visitors import StatementExprExtractor
from klara.klara_z3 import cov_manager
from klara.klara_z3 import inference_extension
from klara.scripts.cover_gen_ins import solver
from klara.scripts.cover_gen_ins.config import ConfigNamespace

MANAGER = cov_manager.CovManager()


class LineFix(solver.DepFinder):
    def __init__(self, *args, **kwargs):
        super(LineFix, self).__init__(*args, **kwargs)
        self.cond_cache = set()

    def visit_call(self, node: nodes.Call):
        MANAGER.logger.info("COV", "Analyzing functioncall at line: {}", node.lineno)
        for target_func in node.func.infer(self.context):
            if isinstance(target_func.result, nodes.FunctionDef):
                target_func.result.called_by.append(node)

    def resolve_func(self, node):
        """resolve function call of any arbitary node.
        It will trace the call chain and load up the context. The caller can happen at more than one place
        :param node:
        :return:
        """
        parent_scope = node.scope()
        while not isinstance(parent_scope, nodes.FunctionDef):
            try:
                parent_scope = parent_scope.scope()
            except AttributeError:
                yield set()
                return
        if parent_scope.name == self.entry_func:
            yield set()
        else:
            if not parent_scope.called_by:
                yield set()
            else:
                for called_node in parent_scope.called_by:
                    conditions = set()
                    self.context.map_call_node_to_func(called_node, parent_scope, self.class_ins, None)
                    try:
                        conditions |= called_node.statement().refer_to_block.conditions
                    except AttributeError:
                        pass
                    for cond in self.resolve_func(called_node):
                        yield conditions | cond

    def fix_all(self):
        for kls in self.classes:
            for stmt in kls.get_statements():
                MANAGER.logger.info("COV", "Fixing stmt: {} at line: {}", stmt, stmt.lineno)
                self.fix_stmt(stmt)

    def fix_stmt(self, stmt):
        total = set()
        block = stmt.statement().refer_to_block
        conditions = block.conditions
        conditions_hash = hash(block)
        if conditions_hash in self.cond_cache:
            return
        self.cond_cache.add(conditions_hash)
        for call_conditions in self.resolve_func(stmt):
            total_cond = conditions | call_conditions
            if total_cond:
                for assumptions, _ in inference_extension.evaluate_paths(total_cond, set(), self.context):
                    if MANAGER.check_assumptions(assumptions) and assumptions:
                        assumptions = list(assumptions)[0] if len(assumptions) == 1 else z3.And(assumptions)
                        total.add(assumptions)
        if total:
            self.ins_collector.add_cond(total, str(conditions))

    def fix_selected_lines(self, linenos: list):
        line_dict = {lineno: (None, None) for lineno in linenos}
        extractor = StatementExprExtractor(line_dict)
        MANAGER.logger.info("LINE-FIX", "fixing lines: {}", linenos)
        value = extractor.extract(self.as_tree)
        stmts = list(value)
        stmts.remove(self.as_tree)
        for stmt in stmts:
            self.fix_stmt(stmt)


def solve(ast_str, config=None):
    cov_config = config or ConfigNamespace()
    with utilities.temp_config(MANAGER, cov_config):
        MANAGER.reload_protocol()
        as_tree = MANAGER.build_tree(ast_str)
        MANAGER.apply_transform(as_tree)
        c = cfg.Cfg(as_tree)
        c.apply_transform()
        c.convert_to_ssa()
        c.fill_all_conditions()
        df = LineFix(c, as_tree)
        if cov_config.cover_lines:
            df.fix_selected_lines(cov_config.cover_lines)
        elif cov_config.cover_all:
            df.fix_all()
        return df.analyze_phi()
