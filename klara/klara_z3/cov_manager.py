"""manager instance for coverage analysis"""
import collections
import contextlib
import os
import pathlib
from typing import List

import z3

from klara.core import cfg
from klara.core import manager, nodes

COV_PLUGINS_DIR = pathlib.Path(__file__).parent / "plugins"

Z3ModelResult = collections.namedtuple("Z3ModelResult", ("sat", "model", "hash", "assumptions"))


class CovManager(manager.AstManager):
    """Coverage specific manager"""

    def _fresh_init(self, config=None):
        super(CovManager, self)._fresh_init(config)
        if not self.__dict__ or "_cov_manager_status" not in self.__dict__ or not self._cov_manager_status:
            # a result cache when solving conditions for sym_nodes
            self.cov_cached = {}
            # explanation please refer to `_ast_manager_status` in manager.AstManager
            self._cov_manager_status = True
            # the rtb constraint read from rtb file.
            self.predicate_expr = True
            # the cache for z3 expression satisfiability checking
            self.z3_cache = {}
            z3.set_option("smt.arith.solver", 2)
            self.z3_solver = z3.SimpleSolver()
            self.z3_assumptions_cache = {}
            self.z3_assumptions_computed_cache = {}
            self._infer_wrapper = lambda x: x
            # caching of abutments cover calculation involving multiple inference results
            self.leaf_cells_dict = {}
            # list of function arguments that is z3 variables
            self._z3_func_args: List[nodes.Arg] = []

    def initialize(self, config=None):
        super(CovManager, self).initialize(config)
        self.initialize_z3()
        self.load_cov_extensions()

    def initialize_z3(self):
        self.predicate_expr = True
        z3.set_option(html_mode=False)
        if self.config.z3_parallel:
            z3.set_param("parallel.enable", True)
            if self.config.z3_parallel_max_threads:
                z3.set_param("parallel.threads.max", self.config.z3_parallel_max_threads)

    def uninitialize(self):
        super(CovManager, self).uninitialize()
        self.disable_infer_check_sat()
        self.z3var_maps.clear()
        self.predicate_expr = True

    def build_cfg(self, as_tree):
        backup_infer_sequence = MANAGER.config.enable_infer_sequence
        MANAGER.config.enable_infer_sequence = False
        c = cfg.Cfg(as_tree)
        c.apply_root_transform()
        c.convert_to_ssa()
        c.fill_all_conditions()
        MANAGER.config.enable_infer_sequence = backup_infer_sequence
        return c

    def check_assumptions_and_get_model(self, assumptions: set):
        """check assumption for satisfiability. Return True if assumptions is empty"""
        self.z3_solver.reset()
        assumptions_hash = hash(frozenset(assumptions))
        assumptions_with_predicate = tuple(assumptions) + (self.predicate_expr,)
        if assumptions_hash in self.z3_assumptions_computed_cache:
            return self.z3_assumptions_computed_cache[assumptions_hash]
        else:
            try:
                self.z3_solver.add(assumptions_with_predicate)
            except z3.Z3Exception:
                pass
            ret = self.z3_solver.check() == z3.sat
            if ret:
                res = Z3ModelResult(ret, self.z3_solver.model(), assumptions_hash, assumptions)
                self.z3_assumptions_computed_cache[assumptions_hash] = res
            else:
                res = Z3ModelResult(ret, None, assumptions_hash, assumptions)
                self.z3_assumptions_computed_cache[assumptions_hash] = res
            return self.z3_assumptions_computed_cache[assumptions_hash]

    def check_assumptions(self, assumptions: set):
        res = self.check_assumptions_and_get_model(assumptions)
        return res.sat

    def add_conditions(self, conditions: set):
        # process the conditions, either convert it to assumption based.
        # but assumption based will significantly slow down when it's complicated enough
        return set(conditions)

    def load_cov_extensions(self):
        """get all file_path of plugins in plugins directory"""
        # load modules in this directory
        for module in sorted(os.listdir(COV_PLUGINS_DIR)):
            if module.endswith(".py"):
                self.logger.info("INITIALIZE", "load cov default specified extension files {}", module)
                self.load_extension(os.path.join(COV_PLUGINS_DIR, module))

    def enable_infer_check_sat(self, infer_check_sat):
        """enable inference system to filter unsat inference path"""
        self._infer_wrapper = infer_check_sat

    def disable_infer_check_sat(self):
        self._infer_wrapper = lambda x: x

    @contextlib.contextmanager
    def initialize_z3_var_from_func(self, func: nodes.FunctionDef):
        """
        Create z3 constant for all arguments in the function, type is based on arg annotation
        """
        self.clear_z3_cache()
        self._z3_func_args = list(func.args.args)
        yield
        self._z3_func_args.clear()
        self.clear_z3_cache()

    def arg_is_z3_var(self, arg: nodes.Arg):
        """
        check if `arg` is initialized as z3 variables
        """
        return arg in self._z3_func_args

    def clear_z3_cache(self):
        self.z3var_maps.clear()
        self.z3_assumptions_computed_cache.clear()


MANAGER = CovManager()
