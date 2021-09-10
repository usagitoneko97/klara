"""utilities for working with plugins/type stub file"""
import os
import pathlib

PLUGINS_DIR = pathlib.Path(__file__).parent.parent / "plugins"


def get_plugins_files():
    """get all file_path of plugins in plugins directory"""
    # load modules in this directory
    results = []
    for module in os.listdir(PLUGINS_DIR):
        if module.endswith(".py"):
            results.append(os.path.join(PLUGINS_DIR, module))
    return results


def get_default_stub_files():
    # load modules in this directory
    results = []
    for module in os.listdir(PLUGINS_DIR):
        if module.endswith(".pyi"):
            results.append(os.path.join(PLUGINS_DIR, module))
    return results


def get_default_typeshed_path():
    return os.path.join(os.path.dirname(__file__), "typeshed")
