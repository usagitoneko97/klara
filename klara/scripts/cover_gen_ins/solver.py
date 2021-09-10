import z3

from klara.core import nodes, recipe, utilities
from klara.klara_z3 import cov_manager, instance_collector, inference_extension
from klara.klara_z3.html import report
from klara.scripts.cover_gen_ins import config

MANAGER = cov_manager.CovManager()
try:
    from klara.core.html import infer_server
except ImportError as e:
    infer_server = None


class DepFinder(recipe.ClassInstanceBuilder):
    """
    For every class, assume the last FunctionDef is the top level method to call.
    And for every instance, only the top level method will be call. This means that
    we could safely assume that every instance has only the attributes coming from __init__
    and the top level method.

    The assumption being made:
    1. Top level method has only `self` arg
    2. Top level method is placed at the last of the class
    3. Only top level method will be called by the class instance. All other method will
        be called only by the top level method

    The overall steps will be carried out:
    1. visit the ClassDef.
    2. Construct an instance and load context with all attributes in __init__
    3. Identify the top level method.
    4. overload phi function infer handler.
    5. Resolve the returned value by the top level method. this will trigger the
        overloaded phi function handler and those are the dependencies required.
    """

    def __init__(self, cfg, as_tree):
        super(DepFinder, self).__init__()
        self.cfg = cfg
        self.ins_collector = instance_collector.InstanceCollector()
        self.entry_class: str = MANAGER.config.entry_class
        self.entry_func: str = MANAGER.config.entry_func
        self.is_multi_processes = MANAGER.config.z3_parallel
        self.processes = MANAGER.config.z3_parallel_max_threads
        self.bound_conditions = []
        # temporary storage to cache the created node to prevent garbage collect binop node
        # this will prevent same binop node created using prev binop node memory space,
        # thus having the same id, which can be problematic with the caching
        self._created_nodes = []
        # all the class node that will be analyze
        self.classes = []
        self.as_tree = as_tree
        self.old_infer = None
        self.initialize()
        self._z3_index = 0
        self._z3_var = {}
        self.z3_opt = z3.Optimize()

    def register_transform(self):
        self.cfg.apply_transform()

    def unregister_transform(self):
        self.cfg.apply_transform()

    def initialize(self):
        """Visit all the class and initialize constructor, and initialize all `self` of bound method"""
        # clear cache used in rename, it'll not be useful to have since during renaming the inference
        # system has not been setup yet.
        MANAGER.clear_infer_cache()
        self.register_transform()
        self.visit(self.as_tree)

    def uninitialize(self):
        self.visit(self.as_tree)

    def visit_classdef(self, node: nodes.ClassDef):
        if self.entry_class == "" or node.name == self.entry_class:
            self.classes.append(node)
            MANAGER.logger.info("COV", "analyzing class: {}.{}", node.name, self.entry_func)
            super(DepFinder, self).visit_classdef(node)

    def solve_classdef(self):
        with MANAGER.logger.info("INFER", "Gathering conditions using inference systems"):
            for cls in self.classes:
                top_level = cls.get_latest_stmt(self.entry_func)
                for ret_val_res in top_level.infer_return_value(self.context):
                    for z3_result, _ in ret_val_res.check_sat(self.context):
                        if z3_result.sat:
                            self.ins_collector.add_cond(z3_result.assumptions, ret_val_res, None)

    def analyze_phi(self, use_z3_check=False):
        # clear all used node and blocks to free up memory
        del self.cfg
        MANAGER.clear_infer_cache()
        with MANAGER.logger.info("COV", "Solving conditions gathered using z3"):
            result = list(
                self.ins_collector.yield_instances(self.is_multi_processes, self.processes, use_z3_check=use_z3_check)
            )
            if MANAGER.config.output_statistics:
                self.ins_collector.report_statistics(MANAGER.config.output_statistics)
            return result

    def compute_arg(self, identifier, ins_collector, conditions, z3_assumptions, context=None):
        """
        :param node_exprs: list of ast nodes
        :return: dict contain ast_node to value
        """
        for cond, _ in inference_extension.evaluate_paths(conditions, z3_assumptions, context):
            if MANAGER.check_assumptions(cond):
                ins_collector.add_cond(cond)


def solve(ast_str, cov_config=None):
    cov_config = cov_config or config.ConfigNamespace()
    with utilities.temp_config(MANAGER, cov_config):
        as_tree = MANAGER.build_tree(ast_str)
        c = MANAGER.build_cfg(as_tree)
        df = DepFinder(c, as_tree)
        df.solve_classdef()
        if cov_config.html_server:
            if not infer_server:
                MANAGER.logger.warning("SERVER", "Please install `flask` to proceed with invoking infer server")
            else:
                MANAGER.logger.info("Running html debugging server. Skipping conditions solver")
                reporter = report.CovAnalysisHtmlReport("", ast_str, as_tree)
                infer_server.run(cov_config.html_server_port, reporter, df.context)
        else:
            return df.analyze_phi(use_z3_check=True)
        df.uninitialize()
