import ast
import pathlib
import re
from textwrap import dedent

from klara.core import _ast, ssa_visitors
from . import nodes
from .base_manager import BaseManager

BASE_MANAGER = BaseManager()


def _bin_op_from_module(module):
    return {
        module.Add: "+",
        module.BitAnd: "&",
        module.BitOr: "|",
        module.BitXor: "^",
        module.Div: "/",
        module.FloorDiv: "//",
        module.Mult: "*",
        module.Pow: "**",
        module.Sub: "-",
        module.LShift: "<<",
        module.RShift: ">>",
        module.Mod: "%",
    }


def _comp_op_from_module(module):
    return {
        module.Lt: "<",
        module.Gt: ">",
        module.LtE: "<=",
        module.GtE: ">=",
        module.Eq: "==",
        module.NotEq: "!=",
        module.Is: "is",
        module.IsNot: "is not",
        module.In: "in",
        module.NotIn: "not in",
    }


def _context_from_module(module):
    return {module.Load: nodes.Load, module.Store: nodes.Store, module.Del: nodes.Del, module.Param: nodes.Load}


def _unary_op_from_module(module):
    return {module.UAdd: "+", module.USub: "-", module.Not: "not", module.Invert: "~"}


def _bool_op_to_module(module):
    return {module.And: "and", module.Or: "or"}


class TreeRewriter:
    def __init__(self, parser_mod=ast, py2=False):
        self._visit_cache = {}
        self._parser_module = parser_mod
        self._py2 = py2
        self._bin_op_classes = _bin_op_from_module(self._parser_module)
        self._comp_op_classes = _comp_op_from_module(self._parser_module)
        self._unary_op_classes = _unary_op_from_module(self._parser_module)
        self._bool_op_classes = _bool_op_to_module(self._parser_module)
        self._context_classes = _context_from_module(self._parser_module)

    def visit(self, node, parent):
        cls = node.__class__
        method = "visit_" + cls.__name__.lower()
        if method not in self._visit_cache:
            if isinstance(node, list):
                # to differentiate between _ast.list and the actual list
                visitor = self.generic_visit
            else:
                visitor = getattr(self, method, self.generic_visit)
            self._visit_cache[cls] = visitor
        else:
            visitor = self._visit_cache[cls]
        return visitor(node, parent)

    def generic_visit(self, node, parent):
        return node

    def _get_context(self, ctx):
        return self._context_classes.get(type(ctx))

    def visit_module(self, node, name="", path=None):
        """The entry method"""
        mod_node = nodes.Module(name=name, path=path)
        mod_node.postinit(body=[self.visit(b, mod_node) for b in node.body])
        return mod_node

    def visit_assign(self, node, parent):
        assign_node = nodes.Assign(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        assign_node.postinit(
            targets=[self.visit(t, assign_node) for t in node.targets], value=self.visit(node.value, assign_node)
        )
        return assign_node

    def visit_augassign(self, node, parent):
        n = nodes.AugAssign(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(self.visit(node.target, n), self._bin_op_classes[type(node.op)], self.visit(node.value, n))
        return n

    def visit_annassign(self, node, parent):
        n = nodes.AnnAssign(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(self.visit(node.target, n), self.visit(node.annotation, n), self.visit(node.value, n), node.simple)
        return n

    def visit_binop(self, node, parent):
        bin_op = nodes.BinOp(
            lineno=getattr(node, "lineno", None), col_offset=getattr(node, "col_offset", None), parent=parent
        )
        bin_op.postinit(
            self.visit(node.left, bin_op), self._bin_op_classes[type(node.op)], self.visit(node.right, bin_op)
        )
        return bin_op

    def visit_constant(self, node, parent):
        return nodes.Const(node.value, getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)

    def visit_num(self, node, parent):
        return nodes.Const(node.n, getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)

    def visit_str(self, node, parent):
        return nodes.Const(node.s, getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)

    def visit_unaryop(self, node, parent):
        n = nodes.UnaryOp(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(self._unary_op_classes[type(node.op)], self.visit(node.operand, n))
        if n.op == "not":
            # not operand should be in boolean context
            n.operand = nodes.Bool.wrap(n.operand)
        return n

    def visit_boolop(self, node, parent):
        n = nodes.BoolOp(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(self._bool_op_classes[type(node.op)], [self.visit(v, n) for v in node.values])
        return n

    def visit_name(self, node, parent):
        name_const_map = {"True": True, "False": False, "None": None}
        n = None
        ctx = self._get_context(node.ctx)
        if node.id in ("True", "False", "None"):
            n = nodes.NameConstant(
                name_const_map[node.id], getattr(node, "lineno", None), getattr(node, "col_offset", None), parent
            )
            return n
        elif ctx is nodes.Load:
            n = nodes.Name(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        elif ctx is nodes.Store:
            n = nodes.AssignName(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        elif ctx is nodes.Del:
            n = nodes.DelName(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(node.id, ctx)
        return n

    def visit_attribute(self, node, parent):
        n = None
        ctx = self._get_context(node.ctx)
        if ctx is nodes.Load:
            n = nodes.Attribute(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        elif ctx is nodes.Store:
            n = nodes.AssignAttribute(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        elif ctx is nodes.Del:
            n = nodes.DelAttribute(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(self.visit(node.value, n), node.attr, ctx)
        return n

    def visit_starred(self, node, parent):
        n = None
        ctx = self._get_context(node.ctx)
        if ctx is nodes.Load:
            n = nodes.Starred(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        elif ctx is nodes.Store:
            n = nodes.AssignStarred(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(self.visit(node.value, n))
        return n

    def visit_functiondef(self, node, parent):
        n = nodes.FunctionDef(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        # decorator is not in the scope of functiondef, but rather parent of functiondef
        n.postinit(
            node.name,
            self.visit(node.args, n),
            [self.visit(body, n) for body in node.body],
            [self.visit(dec, parent) for dec in node.decorator_list],
            self.visit(node.returns, n),
        )
        n.parent.scope().containing_scope.append(n)
        return n

    def visit_lambda(self, node, parent):
        n = nodes.Lambda(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        # decorator is not in the scope of functiondef, but rather parent of functiondef
        n.postinit(self.visit(node.args, n), self.visit(node.body, n))
        n.parent.scope().containing_scope.append(n)
        return n

    def visit_overloadedfunc(self, node, parent):
        n = nodes.OverloadedFunc(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent, node)
        return n

    def visit_arg(self, node, parent):
        n = nodes.Arg(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        # annotation lived in the outer scope
        n.postinit(node.arg, self.visit(node.annotation, parent.scope().parent))
        return n

    def visit_arguments(self, node, parent):
        n = nodes.Arguments(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(
            [self.visit(arg, n) for arg in node.args],
            self.visit(node.vararg, parent),
            [self.visit(kwonlyargs, n) for kwonlyargs in node.kwonlyargs],
            self.visit(node.kwarg, n),
            [self.visit(defaults, n) for defaults in node.defaults],
            [self.visit(kw_defaults, n) for kw_defaults in node.kw_defaults],
        )
        return n

    def visit_classdef(self, node, parent):
        n = nodes.ClassDef(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(
            node.name,
            [self.visit(b, parent) for b in node.bases],
            [self.visit(key, n) for key in node.keywords],
            getattr(node, "starargs", None),
            getattr(node, "kwargs", None),
            [self.visit(b, n) for b in node.body],
            [self.visit(dec, parent) for dec in node.decorator_list],
        )
        n.parent.scope().containing_scope.append(n)
        return n

    def visit_yield(self, node, parent):
        n = nodes.Yield(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(self.visit(node.value, n))
        return n

    def visit_yieldfrom(self, node, parent):
        n = nodes.YieldFrom(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(self.visit(node.value, n))
        return n

    def visit_call(self, node, parent):
        n = nodes.Call(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(
            self.visit(node.func, n),
            [self.visit(child, n) for child in node.args],
            keywords=[self.visit(child, n) for child in node.keywords],
        )
        return n

    def visit_keyword(self, node, parent):
        n = nodes.Keyword(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(
            node.arg,
            self.visit(node.value, n),
        )
        return n

    def visit_pass(self, node, parent):
        n = nodes.Pass(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        return n

    def visit_if(self, node, parent):
        n = nodes.If(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(
            nodes.Bool.wrap(self.visit(node.test, n)),
            [self.visit(b, n) for b in node.body],
            [self.visit(orelse, n) for orelse in node.orelse],
        )
        return n

    def visit_ifexp(self, node, parent):
        n = nodes.IfExp(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(nodes.Bool.wrap(self.visit(node.test, n)), self.visit(node.body, n), self.visit(node.orelse, n))
        return n

    def visit_while(self, node, parent):
        n = nodes.While(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(
            nodes.Bool.wrap(self.visit(node.test, n)), [self.visit(b, n) for b in node.body], self.visit(node.orelse, n)
        )
        return n

    def visit_for(self, node, parent):
        n = nodes.For(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(
            self.visit(node.target, n),
            self.visit(node.iter, n),
            [self.visit(b, n) for b in node.body],
            [self.visit(b, n) for b in node.orelse],
        )
        return n

    def visit_return(self, node, parent):
        n = nodes.Return(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(self.visit(node.value, n))
        try:
            parent.get_parent_of_type(nodes.FunctionDef).return_nodes.append(n)
        except AttributeError:
            # we should raise some exception because it's invalid code
            pass
        return n

    def visit_expr(self, node, parent):
        n = nodes.Expr(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(self.visit(node.value, n))
        return n

    def visit_nameconstant(self, node, parent):
        n = nodes.NameConstant(node.value, getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        return n

    def visit_compare(self, node, parent):
        n = nodes.Compare(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(
            self.visit(node.left, n),
            [self._comp_op_classes[type(op)] for op in node.ops],
            [self.visit(comp, n) for comp in node.comparators],
        )
        return n

    def visit_set(self, node, parent):
        n = nodes.Set(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit([self.visit(elts, n) for elts in node.elts])
        return n

    def visit_list(self, node, parent):
        n = nodes.List(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit([self.visit(elts, n) for elts in node.elts])
        return n

    def visit_tuple(self, node, parent):
        n = nodes.Tuple(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit([self.visit(elts, n) for elts in node.elts])
        return n

    def visit_dict(self, node, parent):
        n = nodes.Dict(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit([self.visit(keys, n) for keys in node.keys], [self.visit(values, n) for values in node.values])
        return n

    def visit_subscript(self, node, parent):
        n = nodes.Subscript(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(self.visit(node.value, n), self.visit(node.slice, n), self.visit(node.ctx, n))
        return n

    def visit_index(self, node, parent):
        n = nodes.Index(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(self.visit(node.value, n))
        return n

    def visit_slice(self, node, parent):
        n = nodes.Slice(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(self.visit(node.lower, n), self.visit(node.upper, n), self.visit(node.step, n))
        return n

    def visit_extslice(self, node, parent):
        n = nodes.ExtSlice(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit([self.visit(d, n) for d in node.dims])
        return n

    def visit_store(self, node, parent):
        n = nodes.Store(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        return n

    def visit_load(self, node, parent):
        n = nodes.Load(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        return n

    def visit_global(self, node, parent):
        n = nodes.Global(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(node.names)
        for name in n.names:
            n.scope().global_var[name] = n.scope()
        return n

    def visit_alias(self, node, parent):
        n = nodes.Alias(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(node.name, node.asname)
        return n

    def visit_import(self, node, parent):
        n = nodes.Import(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit([self.visit(name, n) for name in node.names])
        return n

    def visit_importfrom(self, node, parent):
        n = nodes.ImportFrom(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(node.module, [self.visit(name, n) for name in node.names], node.level)
        return n

    def visit_ellipsis(self, node, parent):
        n = nodes.Ellipsis(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        return n

    def visit_raise(self, node, parent):
        n = nodes.Raise(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(self.visit(node.exc, n), self.visit(node.cause, n))
        return n

    def visit_assert(self, node, parent):
        n = nodes.Assert(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(self.visit(node.test, n), self.visit(node.msg, n))
        return n

    def visit_print(self, node, parent):
        n = nodes.Print(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(self.visit(node.dest, n), [self.visit(v, n) for v in node.values], self.visit(node.nl, n))
        return n

    def visit_delete(self, node, parent):
        n = nodes.Del(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit([self.visit(t, n) for t in node.targets])
        return n

    def visit_try(self, node, parent):
        n = nodes.Try(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(
            [self.visit(b, n) for b in node.body],
            [self.visit(h, n) for h in node.handlers],
            [self.visit(o, n) for o in node.orelse],
            [self.visit(f, n) for f in node.finalbody],
        )
        return n

    def visit_tryfinally(self, node, parent):
        n = nodes.TryFinally(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit([self.visit(b, n) for b in node.body], [self.visit(h, n) for h in node.finalbody])
        return n

    def visit_tryexcept(self, node, parent):
        n = nodes.TryExcept(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(
            [self.visit(b, n) for b in node.body],
            [self.visit(h, n) for h in node.handlers],
            [self.visit(h, n) for h in node.orelse],
        )
        return n

    def visit_excepthandler(self, node, parent):
        n = nodes.ExceptHandler(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(self.visit(node.type, n), node.name, [self.visit(h, n) for h in node.body])
        return n

    def visit_break(self, node, parent):
        return nodes.Break(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)

    def visit_continue(self, node, parent):
        return nodes.Continue(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)

    def visit_with(self, node, parent):
        n = nodes.With(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit([self.visit(i, n) for i in node.items], [self.visit(b, n) for b in node.body])
        return n

    def visit_listcomp(self, node, parent):
        n = nodes.ListComp(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(self.visit(node.elt, n), [self.visit(g, n) for g in node.generators])
        return n

    def visit_setcomp(self, node, parent):
        n = nodes.SetComp(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(self.visit(node.elt, n), [self.visit(g, n) for g in node.generators])
        return n

    def visit_generatorexp(self, node, parent):
        n = nodes.GeneratorExp(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(self.visit(node.elt, n), [self.visit(g, n) for g in node.generators])
        return n

    def visit_dictcomp(self, node, parent):
        n = nodes.DictComp(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(self.visit(node.key, n), self.visit(node.value, n), [self.visit(g, n) for g in node.generators])
        return n

    def visit_comprehension(self, node, parent):
        n = nodes.Comprehension(getattr(node, "lineno", None), getattr(node, "col_offset", None), parent)
        n.postinit(
            self.visit(node.target, n), self.visit(node.iter, n), [self.visit(if_node, n) for if_node in node.ifs]
        )
        return n

    def visit_bytes(self, node, parent):
        try:
            n = nodes.Const(
                node.s.decode("utf-8", "replace"),
                getattr(node, "lineno", None),
                getattr(node, "col_offset", None),
                parent,
            )
            return n
        except UnicodeDecodeError as e:
            BASE_MANAGER.logger.error("AST", 'Error decoding "{}" in line: {}', node.s, node.lineno)
            raise e


class AstBuilder:
    def __init__(self, py2=False, tree_rewriter=None):
        # fill all FunctionDef/ClassDef to locals even without SSA
        self._py2 = py2
        self._tree_rewriter = tree_rewriter or TreeRewriter

    def string_build(self, ast_str, name="", **kwargs):
        old_tree = _ast.parse(dedent(ast_str), self._py2)
        return self._tree_rewriter(parser_mod=_ast.get_parser_module(), py2=self._py2, **kwargs).visit_module(
            old_tree, name=name
        )

    def file_build(self, file_path, relative=False, **kwargs):
        fp = pathlib.Path(file_path)
        return self.string_build(fp.read_text(), **kwargs)


_STATEMENT_SELECTOR = "#@"


def extract_node(code, py2=False):
    """Parses some Python code as a module and extracts a designated AST node.

    # DISCLIAMER: Inspiration taken from astroid project

    Statements:
     To extract one or more statement nodes, append #@ to the end of the line
     To give the extraction a name, append a name after #@

     Examples:
       >>> def x():
       >>>   def y():
       >>>     x = 1    #@ x_constant (value)
       >>>     return 1 #@ an_int_constant

       The return statement will be extracted with a name tuple, constant

       >>> class X(object):
       >>>   def meth(self): #@
       >>>     pass

      The function object 'meth' will be extracted.

    If no statements or expressions are selected, the last toplevel
    statement will be returned.

    If the selected statement is a discard statement, (i.e. an expression
    turned into a statement), the wrapped expression is returned instead.

    For convenience, singleton lists are unpacked.

    :param str code: A piece of Python code that is parsed as
    a module. Will be passed through textwrap.dedent first.
    :param py2: flag to determine ast version
    :returns: The designated node from the parse tree, or a list of nodes, wrapped with namedtuple
    :rtype: namedtuple
    """
    requested_lines = {}
    for idx, line in enumerate(code.splitlines()):
        match = re.match(r".*{}\s*(?P<name>\w*)\s*\(*(?P<member>\w*)\)*".format(_STATEMENT_SELECTOR), line.strip())
        if match:
            name = match.group("name")
            member = match.group("member")
            requested_lines[idx + 1] = name, member

    tree = AstBuilder(py2).string_build(code)
    if not tree.body:
        raise ValueError("Empty tree, cannot extract.")

    if not requested_lines:
        return tree, tree

    statement_extractor = ssa_visitors.StatementExprExtractor(requested_lines)
    value = statement_extractor.extract(tree)
    return tree, value
