import contextlib
import coverage
import importlib
import inspect
import io
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from typing import Callable, Union

import klara
import klara.scripts.cover_gen_ins.__main__ as cov_mod
import klara.scripts.cover_gen_ins.config as cov_config
import klara.scripts.py_check.__main__ as fcf_mod
import klara.scripts.py_check.config as fcf_config
from klara.core import cfg, config, context_mod, inference, manager, nodes, source_utils, tree_rewriter, utilities
from klara.core.tree_rewriter import extract_node
from klara.klara_z3 import cov_manager, inference_extension
from klara.klara_z3.instance_collector import InstanceCollector
from klara.klara_z3.plugins import infer_z3
from klara.klara_z3.z3_nodes import Z3Proxy
from klara.scripts.cover_gen_ins import config, solver
from klara.scripts.cover_gen_ins.line_fix_solver import solve as line_fix_solve
from klara.scripts.cover_gen_ins.solver import solve as cov_solve

from .cfg_helper import build_arbitrary_blocks

MANAGER = manager.AstManager()


class BaseTest(unittest.TestCase):
    """included all assert helper and utilities function"""

    tempdir = tempfile.gettempdir()
    _config_backup = None

    def tearDown(self):
        MANAGER.infer_cache.clear()
        if self._config_backup:
            MANAGER.config = self._config_backup
            self._config_backup = None
        try:
            MANAGER.unload_all_extensions()
            MANAGER.uninitialize()
        except ValueError:
            pass

    @classmethod
    def setUpClass(cls):
        klara.initialize(smt_disable=True)

    def force_initialize(self, c=None, smt_disable=False):
        klara.initialize(c or config.Config(), smt_disable=smt_disable)

    @staticmethod
    def build_arbitrary_blocks(block_links, code=None, block_type=None):
        return build_arbitrary_blocks(block_links, code, block_type)

    def makefile(self, ext, **kwargs):
        ret = None
        for file_name, content in kwargs.items():
            tf = os.path.join(self.tempdir, "{}.{}".format(file_name, ext))
            tf = pathlib.Path(tf)
            tf.touch()
            tf.write_text(content)
            if not ret:
                ret = tf
        return ret

    def makepyfile(self, **kwargs):
        return self.makefile("py", **kwargs)

    def setup_config(self, overwrite=False, config=fcf_config, **kwargs):
        c = config.ConfigNamespace()
        for k, v in kwargs.items():
            setattr(c, k, v)
        if overwrite:
            self._config_backup = MANAGER.config
            MANAGER.config = c
        return c

    def setup_cov_config(self, overwrite=False, **kwargs):
        return self.setup_config(overwrite, cov_config, **kwargs)

    def setup_fcf_config(self, overwrite=False, **kwargs):
        return self.setup_config(overwrite, fcf_config, **kwargs)

    def select_plugin(self, selects):
        selects = selects or []
        default_plugins = filter(lambda a: pathlib.Path(a).stem in selects, list(source_utils.get_plugins_files()))
        for p in default_plugins:
            MANAGER.load_extension(p)


class BaseTestCli(BaseTest):
    def setUp(self):
        self.result = io.StringIO()

    def tearDown(self):
        super(BaseTestCli, self).tearDown()
        self.result.close()

    def run_fcf_with_arg(self, args):
        MANAGER = manager.AstManager()
        MANAGER.unload_all_extensions()
        with MANAGER.temp_manager():
            c = fcf_config.ConfigNamespace()
            fcf_mod.parse_args(args, namespace=c)
            klara.initialize(c, smt_disable=True)
            try:
                fcf_mod.run(c, output_stream=self.result, error_stream=self.result)
            except SystemExit:
                pass
            return self.result.getvalue()

    def run_cov_with_arg(self, args):
        MANAGER = cov_manager.CovManager()
        with MANAGER.temp_manager():
            c = cov_config.ConfigNamespace()
            cov_mod.parse_args(args, namespace=c)
            inference_extension.enable()
            klara.initialize(c)
            c.output_file = self.result
            cov_mod.run(c)
            return self.result.getvalue()


def _arg_to_prm_field(node: nodes.Arg, context=None):
    t = int
    if node.arg == "boolval":
        t = bool
    proxy = infer_z3.Z3Proxy(MANAGER.make_z3_var(node.arg, t))
    yield inference.InferenceResult(proxy, status=True)


_arg_to_prm_field_inf = inference.inference_transform_wrapper(_arg_to_prm_field)


class BaseTestPatchCondResult(BaseTest):
    def setUp(self):
        self.collector = InstanceCollector()
        MANAGER.bool_index = 0
        MANAGER.z3_solver.reset()
        MANAGER.z3_assumptions_cache = {}
        MANAGER.z3_assumptions_computed_cache = {}

    @contextlib.contextmanager
    def register_substitute(self, cfg):
        infer_z3.register()
        MANAGER.register_transform(nodes.Arg, _arg_to_prm_field_inf)
        cfg.apply_transform()
        yield
        MANAGER.unregister_transform(nodes.Arg, _arg_to_prm_field_inf)
        infer_z3.unregister()
        cfg.apply_transform()

    def solve_individual_block(self, ast_str, *block_names):
        MANAGER.config = cov_config.ConfigNamespace()
        MANAGER.config.force_infer = True
        as_tree = tree_rewriter.AstBuilder(MANAGER.config.py_version == 2).string_build(ast_str)
        cfg_real = cfg.Cfg(as_tree)
        cfg_real.apply_transform()
        cfg_real.convert_to_ssa()
        cfg_real.fill_all_conditions()
        with self.register_substitute(cfg_real):
            cfg_real.apply_transform()
            for block_name in block_names:
                block = cfg_real.block_list.get_block_by_name(block_name)
                df = solver.DepFinder(cfg_real, as_tree)
                df.compute_arg(block_name, self.collector, block.conditions, set(), None)

    def assert_individual_block(self, block_name, cond_func: Union[Callable, None]):
        """Assert arg with a lambda. Assert all the ledgers instead of just covered_blk2ledger.
        The lambda will pass a dictionary of the argument
        """
        results = self.collector.use_mss_marco()
        if cond_func is None:
            # passed None, expect no result recorded
            assert not self.collector.all_ledgers
            return
        assert results
        for res in results:
            assert cond_func(res)


class BaseTestInference(BaseTest):
    """provide helper method for testing inference"""

    @classmethod
    def setUpClass(cls):
        from klara.klara_z3.cov_manager import CovManager

        klara.initialize(smt_disable=True)
        cls.COV_MANAGER = CovManager()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.COV_MANAGER.uninitialize()

    @staticmethod
    def build_tree_cfg(source_str, py2=False):
        as_tree, expr = extract_node(source_str, py2)
        MANAGER._reload_protocol(py2)
        MANAGER.apply_transform(as_tree)
        cfg_real = cfg.Cfg(as_tree)
        cfg_real.apply_transform()
        cfg_real.convert_to_ssa()
        cfg_real.fill_all_conditions()
        return expr, cfg_real

    @staticmethod
    def extract_results(results_combination):
        """extract the result from InferenceResult in the container"""
        return_results = []
        for results in results_combination:
            extracted_res = []
            for res in results:
                if res.result.value:
                    extracted_res.append(res.result.value)
                else:
                    extracted_res.append(res.result_type)
            return_results.append(results_combination.__class__(extracted_res))
        return return_results

    @staticmethod
    def extract_const(results_combination):
        """extract the result from InferenceResult in the container. Assume only the first combination"""
        return_results = []
        for results in results_combination:
            container = next(results.extract_const())
            return_results.append(container.strip_inference_result())
        return return_results


def transform_init(func_node: nodes.FunctionDef):
    func_node.name = "__init__"
    return func_node


class DictWrapper:
    def __init__(self, d):
        self.d = d

    def __getitem__(self, item):
        return self.d.get(item, 0)


def is_cfg(subscript_node):
    return (
        str(subscript_node.value) == "self.cfg"
        and subscript_node.scope().type == "method"
        and isinstance(subscript_node.slice.value, nodes.Const)
    )


prm_data = []
PRM_TYPE = {"BOOL": bool, "INT": int, "REAL": float, "STR": str}


def get_prm_type(name):
    for tree in prm_data:
        for i in tree.iter("parameter"):
            if i.get("name") == name:
                returned_type = PRM_TYPE.get(i.get("type"))
                if not returned_type:
                    continue
                return returned_type


@inference.inference_transform_wrapper
def _infer_end_subscript(node: nodes.Subscript, context=None):
    default = None
    if not isinstance(node.slice, nodes.Index) and not isinstance(node.slice.value, nodes.Const):
        raise inference.UseInferenceDefault
    t = get_prm_type(node.slice.value.value)
    if t is None:
        raise inference.UseInferenceDefault

    proxy = Z3Proxy(MANAGER.make_z3_var(node.slice.value.value, t), default)
    if t is bool and context.conditions_mode != context_mod.ConditionsMode.IN_PROGRESS:
        # yield all combinations of the bool, only in non-conditions expanding mode
        ast_true = nodes.Const(True)
        true_branch = inference.InferenceResult.load_result(
            ast_true, bound_conditions={proxy}, selected_operand={hash((node.slice.value.value, t)): ast_true}
        )
        yield true_branch
        ast_false = nodes.Const(False)
        false_branch = inference.InferenceResult.load_result(
            ast_false,
            bound_conditions={proxy.invert_condition()},
            selected_operand={hash((node.slice.value.value, t)): ast_false},
        )
        yield false_branch

    else:
        yield inference.InferenceResult(proxy, status=True)


class BaseCovTest(BaseTestPatchCondResult):
    sample_data_xml = None
    cwd = os.getcwd()
    cov_manager = cov_manager.CovManager()

    def tearDown(self):
        prm_data.clear()

    @classmethod
    def setUpClass(cls):
        super(BaseCovTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        super(BaseCovTest, cls).tearDownClass()

    def init_solver(self, **kwargs):
        prm_data.append(ET.parse(self.sample_data_xml.open()))
        config = self.setup_cov_config(
            py_version=3,
            analyze_procedure=True,
            entry_class="MyClass",
            entry_func="Top",
            enable_infer_sequence=True,
            overwrite=True,
            **kwargs
        )
        inference_extension.enable()
        return config

    def run_solver_with_cov(self, ast_str, max_iterations, expected_coverage=100, expected_return=None, **kwargs):
        config = self.init_solver(**kwargs)
        MANAGER.config = config
        MANAGER.register_transform(nodes.FunctionDef, transform_init, lambda x: x.name == "init")
        MANAGER.register_transform(nodes.Subscript, _infer_end_subscript, is_cfg)
        result = cov_solve(ast_str, cov_config=config)
        self.assertLessEqual(len(result), max_iterations)
        _, filename = tempfile.mkstemp(prefix="test_sample", suffix=".py")
        with open(filename, "w") as file:
            file.write(ast_str)
        spec = importlib.util.spec_from_file_location("test_sample", str(filename))
        module = importlib.util.module_from_spec(spec)
        sys.modules["test_sample"] = module
        coverage_instance = coverage.Coverage(include="*test_sample*")
        coverage_instance.start()
        spec.loader.exec_module(module)
        expected_return = expected_return or list()
        expected_return = list(expected_return)
        for r in result:
            c = module.MyClass()
            c.cfg = DictWrapper(r)
            c.init()
            val = c.Top()
            if val in expected_return:
                expected_return.remove(val)
        assert len(expected_return) == 0, "values: {} has not been return".format(expected_return)
        coverage_instance.stop()
        coverage_percentage = coverage_instance.report()
        if coverage_percentage < expected_coverage:
            parent_function = inspect.getframeinfo(inspect.currentframe().f_back).function
            output_dir = str(self.cwd / ("test_" + str(parent_function)))
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
            os.makedirs(output_dir)
            with open(os.path.join(output_dir, "dump_result.json"), "w") as json_file:
                json.dump(result, json_file, indent=4)
            coverage_instance.html_report(directory=output_dir)
            self.fail(
                "Coverage: {}%, does not match the expected coverage: {}%."
                "\nPlease check directory: {} for coverage information".format(
                    coverage_percentage, expected_coverage, output_dir
                )
            )
        del sys.modules["test_sample"]
        del module
        os.remove(filename)

    def run_and_assert_line_fix(self, ast_str, linenos, func, minimal_len=None, **kwargs):
        config = self.init_solver(**kwargs, cover_lines=linenos)
        MANAGER.register_transform(nodes.FunctionDef, transform_init, lambda x: x.name == "init")
        MANAGER.register_transform(nodes.Subscript, _infer_end_subscript, is_cfg)
        result = line_fix_solve(ast_str, config)
        minimal_len = len(linenos) if minimal_len is None else minimal_len
        assert len(linenos) >= len(result) >= minimal_len
        for res in result:
            assert func(res)
        return result

    def run_fix_all_and_assert_line_fix(self, ast_str, func, **kwargs):
        config = self.init_solver(**kwargs, cover_all=True)
        MANAGER.register_transform(nodes.FunctionDef, transform_init, lambda x: x.name == "init")
        MANAGER.register_transform(nodes.Subscript, _infer_end_subscript, is_cfg)
        result = line_fix_solve(ast_str, config)
        assert result
        for res in result:
            assert func(res)
        return result

    def run_cover_return(self, ast_str, max_iterations, func, lt_flag=False, **kwargs):
        config = self.init_solver(**kwargs)
        MANAGER.register_transform(nodes.FunctionDef, transform_init, lambda x: x.name == "init")
        MANAGER.register_transform(nodes.Subscript, _infer_end_subscript, is_cfg)
        result = cov_solve(ast_str, cov_config=config)
        if lt_flag:
            assert len(result) <= max_iterations
        else:
            assert len(result) == max_iterations
        for res in result:
            assert func(res)

    def run_result_return(self, ast_str, **kwargs):
        config = self.init_solver(**kwargs)
        MANAGER.register_transform(nodes.FunctionDef, transform_init, lambda x: x.name == "init")
        MANAGER.register_transform(nodes.Subscript, _infer_end_subscript, is_cfg)
        with utilities.temp_config(MANAGER, config):
            as_tree = self.cov_manager.build_tree(ast_str)
            c = self.cov_manager.build_cfg(as_tree)
            df = solver.DepFinder(c, as_tree)
            df.solve_classdef()
            for cls in df.classes:
                top_level = cls.get_latest_stmt(df.entry_func)
                yield from top_level.infer_return_value(df.context)
