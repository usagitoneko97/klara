import builtins
import contextlib
import copy
import functools
import pathlib
from runpy import run_path

from klara.core import nodes, utilities
from klara.core.base_manager import BaseManager
from klara.core.config import Config
from klara.core.protocols import (
    BIN_OP_DUNDER_METHOD,
    BIN_OP_METHOD,
    REFLECTED_BIN_OP_DUNDER_METHOD,
    StubTreeRewriter,
    py2_div,
)
from klara.core.source_utils import get_default_stub_files, get_plugins_files
from klara.core.transform import CustomTransform
from klara.core.tree_rewriter import AstBuilder


class AstManager(BaseManager):
    """An ast manager.
    Responsible for:
    - building and caching builtins tree depends on python version,
    - managing the protocol of python operation between python 2/3.
    - managing registering and executing transformation to the tree
    - load default and user specifies extension file, stub file
    """

    BUILTINS_FILE = "typeshed/stdlib/2and3/builtins.pyi"

    def __init__(self, config=None):
        super(AstManager, self).__init__(config)
        # repeating the job of base manager is because there are
        # _fresh_init implementation at this class.
        self.__dict__ = AstManager._core
        self._fresh_init(config)

    def initialize(self, config=None):
        """Initialize all required process for analysis."""
        super(AstManager, self).initialize(config)
        self.config = config
        self.load_default_stub_files()
        self.load_default_extension()
        self.load_user_extension()
        # bootstrap all definition in builtins.pyi
        self.bootstrap_builtins()
        self.reload_protocol()

    def uninitialize(self):
        super(AstManager, self).uninitialize()
        self.weakrefs.clear()

    def bootstrap_builtins(self):
        """Construct builtin class type (e.g. int, float) in ast form
        This will need to only parse builtins.pyi for the class definition,
        and construct the class with appropriate locals method with the return type.
        """
        self.logger.info("INITIALIZE", "constructing builtins ast classes for type inference purposes")

        def builtins_proxy(c):
            return self.builtins_ast_cls[type(c.value)]

        builtins_file = pathlib.PurePath(__file__).parent / self.BUILTINS_FILE
        self.builtins_tree = AstBuilder(tree_rewriter=StubTreeRewriter).file_build(
            builtins_file, py2_version_check=self.config.py_version == 2
        )
        for field in dir(builtins):
            loc = self.builtins_tree.locals.get(field)
            if loc:
                self.builtins_ast_cls[getattr(builtins, field)] = loc
        self.builtins_ast_cls[type(None)] = None
        nodes.Const.obj = property(builtins_proxy)
        nodes.List.obj = self.builtins_ast_cls[list]
        nodes.Dict.obj = self.builtins_ast_cls[dict]
        nodes.Tuple.obj = self.builtins_ast_cls[tuple]
        nodes.Set.obj = self.builtins_ast_cls[set]

    def _fresh_init(self, config=None):
        super(AstManager, self)._fresh_init(config)
        if not self.__dict__ or "_ast_manager_status" not in self.__dict__ or not self._ast_manager_status:
            self.logger.debug("INITIALIZE", "First initialization of ast manager object")
            self.config = config or Config()
            self.transform = CustomTransform()
            self.register_transform = self.transform.register_transform
            self.unregister_transform = self.transform.unregister_transform
            self.built_tree = {}
            self.loaded_extension = set()
            self.loaded_modules = []
            # To indicate the MANAGER for ast has been initialize.
            # This is for cases where base_manager get initialize first
            # and manager._core is filled. Therefore causing the derived manager
            # not initialized.
            self._ast_manager_status = True
            # cache refs of created node so that their id() is unique and hash() will always work
            self.weakrefs = []
            # the variable map from var to z3var for all the conditions
            self.z3var_maps = {}
            # map for default value for each param

    @contextlib.contextmanager
    def temp_manager(self):
        """save the manager state and restore it after the operation."""
        transform_cache = self.transform.transform_cache.copy()
        built_tree = self.built_tree.copy()
        config = copy.copy(self.config)
        loaded_extension = self.loaded_extension.copy()
        yield
        self.transform.transform_cache = transform_cache
        self.built_tree = built_tree
        self.config = config
        self.loaded_extension = loaded_extension

    def apply_transform(self, tree):
        self.logger.debug("AST", "Applying transformation for tree: {}", tree)
        self.transform.visit(tree)

    def build_tree(self, ast_str, name="", tree_rewriter=None):
        self.logger.info("AST", "Converting source code into AST")
        # TODO: implement cache for importing multiple module
        new_tree = AstBuilder(py2=self.config.py_version == 2, tree_rewriter=tree_rewriter).string_build(
            ast_str, name=name
        )
        self.built_tree[name] = new_tree
        self.reload_protocol()
        self.apply_transform(new_tree)
        return new_tree

    def reload_protocol(self):
        """reload all necessary protocol based on config
        reload the dunder method based on py_version in config
        """
        self.logger.debug(
            "INITIALIZE",
            """\
                Reloading dunder method protocol for python {}
                """,
            2 if self.config.py_version else 3,
        )
        self._reload_protocol(self.config.py_version == 2)

    def _reload_protocol(self, py2=False):
        if py2:
            BIN_OP_DUNDER_METHOD["/"] = "__div__"
            REFLECTED_BIN_OP_DUNDER_METHOD["/"] = "__rdiv__"
            BIN_OP_METHOD["/"] = py2_div
        else:
            BIN_OP_DUNDER_METHOD["/"] = "__truediv__"
            REFLECTED_BIN_OP_DUNDER_METHOD["/"] = "__rtruediv__"
            BIN_OP_METHOD["/"] = lambda a, b: a / b

    def load_extension(self, file_path: str):
        """
        simply import the file_obj since it's python file.
        But do some bookkeeping for printing purpose
        :param file_path: the file path in string to import
        :return: None
        """
        p = pathlib.Path(file_path)
        ns = run_path(str(p))
        self.loaded_modules.append(ns)
        reg_func = ns.get("register")
        if reg_func:
            reg_func()
        self.loaded_extension.add(p.name)

    def load_default_extension(self):
        # load default plugins
        for module in get_plugins_files():
            self.logger.info("INITIALIZE", "load default specified extension files {}", module)
            self.load_extension(module)

    def load_user_extension(self):
        # load user specified plugins
        for ext in reversed(self.config.infer_extension_files):
            self.logger.info("INITIALIZE", "load user specified extension files {}", ext)
            self.load_extension(ext.name)

    def load_default_stub_files(self):
        stubs = get_default_stub_files()
        self.config.stubs[0:0] = stubs
        self.logger.info("INITIALIZE", "load the default stub files {}", stubs)

    def unload_all_extensions(self):
        for mod in self.loaded_modules:
            unreg = mod.get("unregister")
            if unreg:
                unreg()
        self.loaded_modules.clear()

    def infer_wrapper(self, func):
        """optional wrapper around infer()"""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return self._infer_wrapper(func)(*args, **kwargs)

        return wrapper

    def add_weak_ref(self, obj):
        self.weakrefs.append(obj)

    def make_z3_var(self, var: str, t):
        """make a z3 field for python variable"""
        if var in self.z3var_maps:
            return self.z3var_maps[var]
        dtype = utilities.AST2Z3TYPE_MAP.get(t)
        if dtype:
            z3var = dtype(var)
            self.z3var_maps[var] = z3var
            return z3var
        else:
            raise NotImplementedError("Type other than int, float, bool and string is not supported yet!")

    def dump_infer(self, node, results, len_after):
        if self.config.statistics:
            self.config.statistics.write("{} LINE {} -> {} -> {}\n".format(node, node.lineno, results, len_after))
