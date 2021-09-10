from collections import OrderedDict, defaultdict

import z3

from klara.core import utilities
from .cov_manager import CovManager

MANAGER = CovManager()


class InstanceCollector:
    def __init__(self):
        self.root = None
        self.all_blocks = []
        self.all_ledgers = set()
        # blocks covered to ledger mapping. Select only 1 ledger
        self.covered_blk2ledger = OrderedDict()
        # blk to blk_covered mapping. For ease of accessing.
        self.blk2blk_covered = defaultdict(set)
        self.vars_sequence = []
        self.removed_block = set()
        self.conditions = {}
        self.failed_conditions = set()
        self.passed_conditions = set()

    def add_cond(self, cond: set, result=None, after_res=None):
        rs = str(result)
        after_res = str(after_res)
        if cond:
            self.conditions[tuple(cond)] = (rs, after_res)

    def _add_result(self, model):
        result = {}
        for prm_var, z3_var in MANAGER.z3var_maps.items():
            z3_result = model[z3_var]
            if z3_result is not None:
                py_val = utilities.get_py_val_from_z3_val(z3_result)
                result[prm_var] = py_val
        return result

    def build_constraints(self, conditions=None):
        """for all conditions, create tracking bool"""
        conditions = conditions or self.conditions
        for i, c in enumerate(conditions):
            yield (z3.Bool("track_{}".format(i)), c)

    def z3_get_all_solutions(self):
        self.failed_conditions.clear()
        if MANAGER.predicate_expr is not None:
            with MANAGER.logger.info("Z3", "Applying rtb expression to all constraints"):
                conditions = self.wrap_conditions()
                conditions = {z3.And(cond, MANAGER.predicate_expr) for cond in conditions}
        solutions = []
        constraints = set(self.build_constraints(conditions))
        while constraints:
            o = z3.Optimize()
            s = 0
            for (tracker, condition) in constraints:
                if type(condition) is list:
                    for c in condition:
                        o.add(z3.Implies(tracker, c))
                else:
                    o.add(z3.Implies(tracker, condition))
                s = s + z3.If(tracker, 1, 0)
            o.maximize(s)
            remaining = set()
            r = o.check()
            if r == z3.sat:
                m = o.model()
                result = self._add_result(m)
                if result:
                    solutions.append(result)
                for (tracker, condition) in constraints:
                    if not m[tracker]:
                        remaining.add((tracker, condition))
            else:
                MANAGER.logger.info("solve for equation: {} returned: {}", s.sexpr(), r)
                return {}
            if constraints == remaining:
                # no further solutions found. Break to avoid infinite loop
                MANAGER.logger.debug("Z3", "Failed to solve the remaining conditions: {}", remaining)
                break
            constraints = remaining
        self.failed_conditions |= constraints
        return solutions

    def yield_instances(self, is_multi_processes=False, processes=None, use_z3_check=False):
        if MANAGER.config.output_statistics:
            with MANAGER.logger.info("COV", "Dumping constraints collected to file"):
                self.report_statistics(MANAGER.config.output_statistics)
        MANAGER.logger.info("COV", "minimizing total of {} conditions", len(self.conditions))
        if use_z3_check:
            return self.use_z3_check()
        mss_alg = {"z3": self.use_mss_z3, "legacy": self.z3_get_all_solutions}
        alg = mss_alg[MANAGER.config.mss_algorithm]
        with MANAGER.logger.info("COV", "using {} to solve for mss", MANAGER.config.mss_algorithm):
            return alg()

    def report_statistics(self, file):
        file.write("PASSED\n")
        file.write("\n\n".join(("    " + p for p in sorted(str(p) for p in self.conditions.keys()))))
        file.write("\n\n\n")
        file.write("FAILED\n")
        file.write("\n\n".join(("    " + p for p in sorted(str(p) for p in self.failed_conditions))))

    def wrap_conditions(self):
        """wrap all conditions set with z3.And to get a valid z3 expr"""
        result = []
        for cond in self.conditions:
            if isinstance(cond, (set, list, tuple)):
                if len(cond) > 1:
                    result.append(z3.And(cond))
                else:
                    result.append(tuple(cond)[0])
            else:
                result.append(cond)
        return result

    def use_z3_check(self):
        """No minimizing instances, just get instance using `solver.check()` on all conditions"""
        results = []
        for cond, ret_result in self.conditions.items():
            z3_result = MANAGER.check_assumptions_and_get_model(cond)
            if z3_result.sat:
                result = self._add_result(z3_result.model)
                results.append(result)
                result["#return-subs"] = ret_result[1]
                result["#return-ori"] = ret_result[0]
        return results

    def use_mss_z3(self):
        soft_constraints = self.wrap_conditions()
        if MANAGER.predicate_expr is not None:
            hard_constraints = MANAGER.predicate_expr
        else:
            hard_constraints = z3.BoolVal(True)
        solver = MSSSolver(hard_constraints, soft_constraints)
        results = []
        for lits in solver.enumerate_sets():
            cons = [soft_constraints[j] for j in lits]
            if MANAGER.z3_solver.check(*cons) == z3.sat:
                result = self._add_result(MANAGER.z3_solver.model())
                if result:
                    results.append(result)
        return results


class MSSSolver:
    """
    Code from:https://raw.githubusercontent.com/Z3Prover/z3/master/examples/python/mus/mss.py
    MIT licensed
    The following is a procedure for enumerating maximal satisfying subsets.
    It uses maximal resolution to eliminate cores from the state space.
    Whenever the hard constraints are satisfiable, it finds a model that
    satisfies the maximal number of soft constraints.
    During this process it collects the set of cores that are encountered.
    It then reduces the set of soft constraints using max-resolution in
    the style of [Narodytska & Bacchus, AAAI'14]. In other words,
    let F1, ..., F_k be a core among the soft constraints F1,...,F_n
    Replace F1,.., F_k by
    F1 or F2, F3 or (F2 & F1), F4 or (F3 & (F2 & F1)), ...,
    F_k or (F_{k-1} & (...))
    Optionally, add the core ~F1 or ... or ~F_k to F
    The current model M satisfies the new set F, F1,...,F_{n-1} if the core is minimal.
        Whenever we modify the soft constraints by the core reduction any assignment
    to the reduced set satisfies a k-1 of the original soft constraints.

    """

    def __init__(self, hard, soft):
        self.s = z3.Solver()
        self.varcache = {}
        self.idcache = {}

        self.n = len(soft)
        self.soft = soft
        self.s.add(hard)
        self.soft_vars = set([self.c_var(i) for i in range(self.n)])
        self.orig_soft_vars = set([self.c_var(i) for i in range(self.n)])
        self.s.add([(self.c_var(i) == soft[i]) for i in range(self.n)])

    def enumerate_sets(self):
        while True:
            if z3.sat == self.s.check():
                MSS = self.grow()
                yield [self.idcache[s] for s in MSS]
            else:
                break

    def c_var(self, i):
        if i not in self.varcache:
            v = z3.Bool(str(self.soft[abs(i)]))
            self.idcache[v] = abs(i)
            if i >= 0:
                self.varcache[i] = v
            else:
                self.varcache[i] = z3.Not(v)
        return self.varcache[i]

    # Retrieve the latest model
    # Add formulas that are true in the model to
    # the current mss

    def update_unknown(self):
        self.model = self.s.model()
        new_unknown = set([])
        for x in self.unknown:
            if z3.is_true(self.model[x]):
                self.mss.append(x)
            else:
                new_unknown.add(x)
        self.unknown = new_unknown

    # Create a name, propositional atom,
    #  for formula 'fml' and return the name.

    def add_def(self, fml):
        name = z3.Bool("%s" % fml)
        self.s.add(name == fml)
        return name

    # replace Fs := f0, f1, f2, .. by
    # Or(f1, f0), Or(f2, And(f1, f0)), Or(f3, And(f2, And(f1, f0))), ...

    def relax_core(self, Fs):
        assert Fs <= self.soft_vars
        prefix = z3.BoolVal(True)
        self.soft_vars -= Fs
        Fs = [f for f in Fs]
        for i in range(len(Fs) - 1):
            prefix = self.add_def(z3.And(Fs[i], prefix))
            self.soft_vars.add(self.add_def(z3.Or(prefix, Fs[i + 1])))

    # Resolve literals from the core that
    # are 'explained', e.g., implied by
    # other literals.

    def resolve_core(self, core):
        new_core = set([])
        for x in core:
            if x in self.mcs_explain:
                new_core |= self.mcs_explain[x]
            else:
                new_core.add(x)
        return new_core

    # Given a current satisfiable state
    # Extract an MSS, and ensure that currently
    # encountered cores are avoided in next iterations
    # by weakening the set of literals that are
    # examined in next iterations.
    # Strengthen the solver state by enforcing that
    # an element from the MCS is encountered.

    def grow(self):
        self.mss = []
        self.mcs = []
        self.nmcs = []
        self.mcs_explain = {}
        self.unknown = self.soft_vars
        self.update_unknown()
        cores = []
        while len(self.unknown) > 0:
            x = self.unknown.pop()
            is_sat = self.s.check(self.mss + [x] + self.nmcs)
            if is_sat == z3.sat:
                self.mss.append(x)
                self.update_unknown()
            elif is_sat == z3.unsat:
                core = self.s.unsat_core()
                core = self.resolve_core(core)
                self.mcs_explain[z3.Not(x)] = {y for y in core if not z3.eq(x, y)}
                self.mcs.append(x)
                self.nmcs.append(z3.Not(x))
                cores += [core]
            else:
                print("solver returned %s" % is_sat)
                exit()
        mss = [x for x in self.orig_soft_vars if z3.is_true(self.model[x])]
        mcs = [x for x in self.orig_soft_vars if not z3.is_true(self.model[x])]
        self.s.add(z3.Or(mcs))
        core_literals = set([])
        cores.sort(key=lambda element: len(element))
        for core in cores:
            if len(core & core_literals) == 0:
                self.relax_core(core)
                core_literals |= core
        return mss
