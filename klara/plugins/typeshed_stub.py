"""plugins for inferring all the type defined in typeshed projects,
and also user defined stubs.
uses stub file defined from the project :(https://github.com/python/typeshed)
typeshed is clone into klara/core/typeshed

The general approach:
1. Locate the typeshed directory, file will be parsed by StubTreeRewriter,
    and loaded into the filename's namespace.
2. setup predicate for detecting usage of the method of the loaded library.
3. Any reference to the loaded module will result in a search in the namespace
"""
import io
import os
import pathlib
import sys
from functools import partial
from typing import Union

from klara.core import inference, manager, nodes, protocols, source_utils, tree_rewriter

MANAGER = manager.AstManager()


class AlwaysIn:
    """Dirty (?) kind of hack to represent `select all` modules"""

    def __contains__(self, item):
        return True


def compile_stub(file_path: Union[str, pathlib.Path]):
    fp = pathlib.Path(file_path)
    built_tree = tree_rewriter.AstBuilder(py2=False, tree_rewriter=protocols.StubTreeRewriter).string_build(
        fp.read_text(), name=fp.stem, py2_version_check=MANAGER.config.py_version
    )
    return built_tree


class TypeShed:
    """Typeshed discovery/loading class"""

    def __init__(self, typeshed_path=None, selected_mods: list = None):
        """
        :param typeshed_path: custom path to typeshed directory
        :param selected_mods: list of selected module to load. ["ALL"] to select all
        """
        super(TypeShed, self).__init__()
        self._root = typeshed_path or source_utils.get_default_typeshed_path()
        self.built_module = {}
        selected_mods = selected_mods or []
        if len(selected_mods) > 0 and selected_mods[0] == "ALL":
            self.selected_mods = AlwaysIn()
        else:
            self.selected_mods = selected_mods

    def _load_file(self, path):
        file_path = os.path.join(self._root, path)
        with open(file_path, "rb") as f:
            return file_path, f.read()

    def get_module_file(self, toplevel, module, version):
        """Get the contents of a typeshed file, with the filename ending with .pyi
        :param toplevel: the top-level directory within typeshed/, typically "builtins",
        "stdlib" or "third_party".
        :param module: module name (e.g., "sys" or "__builtins__"). Can contain dots, if
        it's a submodule.
        :param version: The Python version. (major, minor)
        :return: A tuple with the filename and contents of the file
        """
        module_path = os.path.join(*module.split("."))
        versions = ["%d.%d" % (version[0], minor) for minor in range(version[1], -1, -1)]
        # E.g. for Python 3.5, try 3.5/, 3.4/, 3.3/, ..., 3.0/, 3/, 2and3.
        # E.g. for Python 2.7, try 2.7/, 2.6/, ..., 2/, 2and3.
        # The order is the same as that of mypy. See default_lib_path in
        # https://github.com/JukkaL/mypy/blob/master/mypy/build.py#L249
        for v in versions + [str(version[0]), "2and3"]:
            path_rel = os.path.join(toplevel, v, module_path)
            for path in [os.path.join(path_rel, "__init__.pyi"), path_rel + ".pyi"]:
                try:
                    name, src = self._load_file(path)
                    return name, src
                except IOError:
                    pass

    def get_all_module_path(self, version):
        """
        :param version: python (major, minor)
        :return: list of type stub file path
        """
        typeshed_dirs = ("stdlib", "third_party")
        for td in typeshed_dirs:
            versions = ["%d.%d" % (version[0], minor) for minor in range(version[1], -1, -1)]
            for v in versions + [str(version[0]), "2and3"]:
                td_path = pathlib.Path(self._root) / td / v
                for mod in td_path.glob("**/*.pyi"):
                    yield mod

    @classmethod
    def compile_typeshed_file(cls, *args, **kwargs):
        c = cls(*args, **kwargs)
        py_version = (MANAGER.config.py_version, 7) if MANAGER.config.py_version == 2 else sys.version_info
        for mod in c.get_all_module_path(py_version):
            if mod.stem in c.selected_mods:
                built_tree = compile_stub(mod)
                c.built_module[mod.stem] = built_tree
        return c


def _typeshed_import_predicate(node: nodes.Import, module: str):
    for name in node.names:
        if str(name.name) == module:
            return True
    return False


def _infer_import(node: nodes.Import, typeshed_ast, context=None):
    if typeshed_ast:
        yield inference.InferenceResult.load_result(typeshed_ast)
    else:
        raise inference.UseInferenceDefault()


def register_stub(file: Union[str, pathlib.Path, io.StringIO]):
    fp = pathlib.Path(file)
    built_tree = compile_stub(fp)
    MANAGER.register_transform(
        nodes.Import,
        inference.inference_transform_wrapper(partial(_infer_import, typeshed_ast=built_tree)),
        partial(_typeshed_import_predicate, module=fp.stem),
    )


def register():
    # load typeshed directory
    ts_handler = TypeShed.compile_typeshed_file(selected_mods=MANAGER.config.typeshed_select)
    # load user defined stubs
    for stub_file in MANAGER.config.stubs:
        if isinstance(stub_file, io.TextIOBase):
            stub_file = stub_file.name
        stub_path = pathlib.Path(stub_file)
        register_stub(stub_path)

    for mod_name, mod_ast in ts_handler.built_module.items():
        MANAGER.register_transform(
            nodes.Import,
            inference.inference_transform_wrapper(partial(_infer_import, typeshed_ast=mod_ast)),
            partial(_typeshed_import_predicate, module=mod_name),
        )
