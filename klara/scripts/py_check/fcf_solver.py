from Common import common
from klara.core import exceptions, manager, nodes, protocols
from klara.core.cfg import ParentScopeBlock
from klara.core.context_mod import InferenceContext
from klara.core.ssa_visitors import AstVisitor
from klara.core.utilities import methdispatch

from .config import ConfigNamespace
from .html import report
from .result_banner import decorate
from .terminal import TerminalFormatter

MANAGER = manager.AstManager()
try:
    from klara.core.html import infer_server
except ImportError as e:
    infer_server = None


class WarningItem:
    __slots__ = ("value", "value_repr", "col_offset", "optional_type", "infer_path")

    def __init__(self, value, value_repr, col_offset, optional_type=None, infer_path=None):
        self.value = value
        self.value_repr = value_repr
        self.col_offset = col_offset
        self.infer_path = infer_path or []
        if optional_type is not None:
            self.optional_type = optional_type
        else:
            self.optional_type = type(self.value)


class FloatWarningResult(common.DefaultOrderedDict):
    def __init__(self):
        super(FloatWarningResult, self).__init__(FloatWarningInFile)

    def get_warning(self, relative_path):
        return self[relative_path]

    @methdispatch
    def add_entry(self, relative_path, trace_as_key, actual_trace, col_offset, lineno, value, value_repr):
        warning = self.get_warning(relative_path)
        warning.add_entry(trace_as_key, actual_trace, col_offset, lineno, value, value_repr)

    @add_entry.register(WarningItem)
    def _(self, warning_item, relative_path, trace_as_key, actual_trace, lineno):
        warning = self.get_warning(relative_path)
        warning.add_entry(warning_item, lineno, trace_as_key, actual_trace)


class FloatWarningInFile(common.DefaultOrderedDict):
    def __init__(self):
        super(FloatWarningInFile, self).__init__(FloatWarningInTrace)

    def get_warning(self, trace_as_key):
        return self[trace_as_key]

    @methdispatch
    def add_entry(self, trace_as_key, actual_trace, col_offset, lineno, value, value_repr):
        warning = self.get_warning(trace_as_key)
        warning.add_entry(lineno, col_offset, value, value_repr, actual_trace)

    @add_entry.register(WarningItem)
    def _(self, warning_item, lineno, trace_as_key, actual_trace):
        warning = self.get_warning(trace_as_key)
        warning.add_entry(warning_item, lineno, actual_trace)


class FloatWarningInTrace:
    """contain all warnings within 1 stack trace"""

    def __init__(self):
        self.trace = None
        self.warning = common.DefaultOrderedDict(list)

    @methdispatch
    def add_entry(self, lineno, col_offset, value, value_repr, actual_trace=None):
        if actual_trace is not None:
            self.trace = actual_trace
        self.add_warning_item(lineno, WarningItem(value, value_repr, col_offset))

    @add_entry.register(WarningItem)
    def _(self, warning_item, lineno, actual_trace):
        if actual_trace is not None:
            self.trace = actual_trace
        self.add_warning_item(lineno, warning_item)

    def add_warning_item(self, lineno, warning_item):
        warning = self.warning[lineno]
        warning.append(warning_item)


class ComparisonAstSolver(AstVisitor):
    def __init__(self, trace, node, file_name="", context=None, result=None, file_path="", float_config=None):
        super(ComparisonAstSolver, self).__init__()
        self.node = node
        self.result = result
        self.trace = trace
        self.file_name = file_name
        self.context = context
        self.file_path = file_path
        self.float_config = float_config or ConfigNamespace()

    @classmethod
    def solve(cls, node, trace, file_name="", context=None, result=None, file_path="", float_config=None):
        c = cls(trace, node, file_name, context, result, file_path, float_config)
        c.visit(node)
        return c

    def process_variable(self, operand):
        for possible_val in operand.infer(self.context):
            if possible_val.result_type == MANAGER.builtins_ast_cls[float]:
                MANAGER.logger.info(
                    "FCF",
                    """\
                        operand: '{}' in stmt '{}' has floating operand: {}""".format(
                        operand, operand.statement(), possible_val
                    ),
                )
                self.trace.add_trace(FrameInfo(self.file_name, self.node, operand.lineno, None, operand.scope()))
                try:
                    warning_item = WarningItem(
                        possible_val.result.value, str(operand), operand.col_offset, float, possible_val.infer_path
                    )
                except AttributeError:
                    # the case of type inference
                    warning_item = WarningItem(
                        "Unknown value", str(operand), operand.col_offset, float, possible_val.infer_path
                    )

                self.result.add_entry(warning_item, self.file_path, str(self.trace), self.trace, operand.lineno)

    def visit_compare(self, node):
        left = node.left
        if isinstance(left, nodes.Compare):
            self.visit_compare(left)
        for (operator, operand) in zip(node.ops, node.comparators):
            # get the dunder method if presented
            try:
                # avoid solving the compare node if it's dunder method
                if len(list(protocols.get_custom_dunder_method(left, operator, self.context))) > 0:
                    continue
            except (exceptions.DunderUnimplemented, exceptions.OperationIncompatible):
                pass
            if operator not in self.float_config.get_operator_involved():
                left = operand
                continue
            self.process_variable(left)
            if isinstance(operand, nodes.Compare):
                self.visit_compare(operand)
            self.process_variable(operand)
            left = operand


class StackSummary(list):
    """stack that contain FrameInfo as element"""

    def extract_trace(self):
        """return a copy of traceback"""
        return self.copy()

    def add_trace(self, trace):
        if len(self) > 0:
            top_trace = self[-1]
            if top_trace.is_same_trace(trace):
                return
        self.append(trace)

    @classmethod
    def from_list(cls, stack_list):
        c = cls()
        c.extend(stack_list.copy())
        return c

    def copy(self):
        stack_list = super(StackSummary, self).copy()
        s = StackSummary.from_list(stack_list)
        return s


class FrameInfo:
    def __init__(self, filename="", line="", lineno=-1, _locals=None, name=""):
        self.filename = filename
        self.line = line
        self.lineno = lineno
        self.locals = _locals
        self.name = name

    def is_same_trace(self, other):
        return (
            (self.filename == other.filename)
            and (self.line == other.line)
            and (self.lineno == other.lineno)
            and (self.name == other.name)
        )


class ComparisonSolver(AstVisitor):
    def __init__(self, file_path="", context=None, float_config=None):
        self.result = FloatWarningResult()
        self.stack_trace = StackSummary()
        self.file_path = file_path
        self.context = context if context else InferenceContext()
        self.float_config = float_config or ConfigNamespace()
        self.dunder_methods = {}
        self._visited_blk = []
        # prevent recursive call
        self._call_cache = []

    def visit_compare(self, node):
        left = node.left
        self.generic_visit(node)
        for (operator, operand) in zip(node.ops, node.comparators):
            try:
                dunder_methods = list(protocols.get_custom_dunder_method(left, operator, self.context))
                for meth in dunder_methods:
                    self.context.map_args_to_func(left, operand, func_node=meth)
                self.dunder_methods.setdefault(node, []).extend(dunder_methods)
            except (exceptions.DunderUnimplemented, exceptions.OperationIncompatible):
                pass

    def visit_binop(self, node):
        self.generic_visit(node)
        try:
            dunder_methods = list(protocols.get_custom_dunder_method(node.left, node.op, self.context))
            for meth in dunder_methods:
                self.context.map_args_to_func(node.left, node.right, func_node=meth)
            self.dunder_methods.setdefault(node, []).extend(dunder_methods)
        except (exceptions.DunderUnimplemented, exceptions.OperationIncompatible):
            pass

    def visit_call(self, node):
        if node in self._call_cache:
            return
        self._call_cache.append(node)
        for dest_def_result in node.func.infer(self.context):
            dest_def = dest_def_result.result
            if not isinstance(dest_def, nodes.Uninferable):
                self.context.reload_context(node, dest_def, node.func.instance())
                self.context.add_call_chain(node, dest_def)
                if dest_def.refer_to_block is not None:
                    # if refer_to_block is None, it might be referring to built in method (e.g. list.append())
                    self.solve_root(dest_def.refer_to_block)
                self.context.remove_call_chain(node)

    def solve_root(self, root):
        if not root:
            return
        elif isinstance(root, ParentScopeBlock):
            self._visited_blk.append(root)
            node = root.ast_node
            if node.parent:
                # node.parent not None means that this frame is not the top
                self.stack_trace.append(FrameInfo(self.file_path, node, node.lineno, None, node.parent.scope()))
            self._solve_root(root)
            if not self.float_config.no_analyze_procedure:
                for containing_scope in root.ast_node.containing_scope:
                    # only solve those function/method that haven't get called
                    if containing_scope.refer_to_block not in self._visited_blk:
                        self.solve_root(containing_scope.refer_to_block)
            self.stack_trace.pop() if node.parent else None
        else:
            self._solve_root(root)

    def _solve_root(self, root):
        for block in root.blocks:
            for code in block.get_code_to_analyse():
                self.visit(code)
                dunder_methods = self.dunder_methods
                self.dunder_methods = {}
                for node, meths in dunder_methods.items():
                    for m in meths:
                        if m.refer_to_block:
                            self.context.add_call_chain(node, m)
                            self.solve_root(m.refer_to_block)
                            self.context.remove_call_chain(node)
                ComparisonAstSolver.solve(
                    code,
                    self.stack_trace.copy(),
                    self.file_path,
                    self.context,
                    result=self.result,
                    file_path=self.file_path,
                    float_config=self.float_config,
                )


@decorate("float comparison")
def solve(cfg, as_tree, ast_str, file_path, args):
    context = InferenceContext()
    context.config = args
    comp_solver = ComparisonSolver(file_path, context, float_config=args)
    comp_solver.solve_root(cfg.root)
    result = comp_solver.result.get(file_path)
    tf = TerminalFormatter(file_path, comp_solver.result, args)
    out = tf.get_error_result_on_path(ast_str, result)
    out += tf.get_summary()
    html_reporter = report.PyCheckHtmlReport(
        file_path, ast_str, as_tree, float_warnings=comp_solver.result.get(file_path)
    )
    if args.html_dir:
        MANAGER.logger.info("HTML", "generating html static files to {}", args.html_dir)
        html_reporter.generate_static_html(args.html_dir)
    if args.html_server:
        if not infer_server:
            MANAGER.logger.warning("SERVER", "Please install `flask` to proceed with invoking infer server")
        else:
            MANAGER.logger.info("HTML", "starting up infer server at localhost:{}", args.html_server_port)
            infer_server.run(args.html_server_port, html_reporter, comp_solver.context)
    return out + "\n" if out else ""
