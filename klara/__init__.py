"""Klara is a automatic test case generator"""
from collections import namedtuple

from klara.core import inference
from klara.core import manager as _core_manager
from klara.core.nodes import *
from klara.core.tree.infer_proxy import InferProxy
from klara.core.tree_rewriter import extract_node as _extract_node
from klara.klara_z3 import cov_manager as _manager
from klara.klara_z3 import inference_extension as _infer_extension
from klara.scripts.cover_gen_ins.config import ConfigNamespace as Config


def initialize(config: Config = None, smt_disable: bool = False) -> None:
    """initialize klara to a different configuration
    :param config: a config object of type Klara.Config to fine tune configuration
    :param smt_disable: disable z3 solver support
    :return: None
    """
    if smt_disable:
        manager = _core_manager.AstManager()
        manager.initialize(config or Config())
        _infer_extension.disable()
    else:
        MANAGER.initialize(config or Config())
        _infer_extension.enable()


MANAGER = _manager.CovManager()
"""A Central manager responsible to cache result, and various common operation across module"""

initialize()


def parse(source: str, py2: bool = False) -> Module:
    """parse python code as ast, apply analysis transformation and return modified tree
    :param source: python source file as string
    :param py2: True if `source` is python 2, False if it's in python 3
    :return: a modified abstract syntax tree with inference support
    """
    MANAGER.config.py_version = 2 if py2 else 3
    tree = MANAGER.build_tree(source)
    MANAGER.build_cfg(tree)
    return tree


def parse_node(source: str, py2: bool = False) -> namedtuple:
    """using :py:func:`tree_rewriter.extract_node` to extract special comment in the source. Please
    refer to the related doc for more info.

    :param str source: A piece of Python code that is parsed as a module. Will be passed through textwrap.dedent first.
    :param py2: flag to determine ast version
    :returns: The designated node from the parse tree, or a list of nodes, wrapped with namedtuple
    :rtype: namedtuple
    """
    MANAGER.config.py_version = 2 if py2 else 3
    MANAGER.reload_protocol()
    tree, value = _extract_node(source, py2)
    MANAGER.apply_transform(tree)
    MANAGER.build_cfg(tree)
    return value
