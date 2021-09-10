from textwrap import dedent

from klara.core import nodes, recipe
from .result_banner import decorate


class CalledFuncGetter(recipe.ClassInstanceBuilder):
    def __init__(self):
        super(CalledFuncGetter, self).__init__()
        self.called_func = []

    def visit_call(self, node):
        for target_func in node.func.infer(self.context):
            if target_func.status:
                self.called_func.append(target_func.result)

    @staticmethod
    def get(node):
        cfg = CalledFuncGetter()
        cfg.visit(node)
        return cfg.called_func


class LoopDetector(recipe.ClassInstanceBuilder):
    def __init__(self):
        super(LoopDetector, self).__init__()
        self.loop_nodes = []
        # a flag to carry out validation only the content of
        self._do_validate = False

    def visit_classdef(self, node: nodes.ClassDef):
        self._do_validate = True
        super(LoopDetector, self).visit_classdef(node)
        self._do_validate = False

    def append_result(self, result):
        if self._do_validate:
            self.loop_nodes.append(result)

    @staticmethod
    def detect(node):
        ld = LoopDetector()
        ld.visit(node)
        return ld.loop_nodes

    def visit_for(self, node):
        self.append_result((node, "for loop detected!"))
        self.generic_visit(node)

    def visit_while(self, node):
        self.append_result((node, "while loop detected!"))
        self.generic_visit(node)

    @staticmethod
    def check_func_body(body, cur_func):
        """check if the body contain call to cur_func"""
        for b in body:
            for func in CalledFuncGetter.get(b):
                if func == cur_func:
                    return b, func
        raise ValueError("{} does not contain call from {}".format(body, cur_func))

    def visit_call(self, node):
        """
        Check specifically for 2 scenario
        1. when node.func is node.scope() (called itself)
        2. when node.func contains call that called node.scope()
        """
        for target_func in node.func.infer(self.context):
            if target_func.status:
                if target_func.result == node.scope():
                    self.append_result((node, "recursive call to {}\n".format(target_func.result)))
                elif isinstance(target_func.result, nodes.FunctionDef):
                    try:
                        body, cur_func = self.check_func_body(target_func.result.body, node.scope())
                        self.append_result(
                            (
                                node,
                                dedent(
                                    """\
                        call to <{}> contains calls: {} to <{}> which is recursive.
                        """.format(
                                        target_func.result, body, cur_func
                                    )
                                ),
                            )
                        )
                    except ValueError:
                        pass


def _format_node(file, loop_node):
    res = str(loop_node[1])
    res += "File: " + file + "\n"
    res += "In line: " + str(loop_node[0].lineno) + "\n"
    res += str(loop_node[0]) + "\n\n"
    return res


@decorate("Loop Detector")
def solve(cfg, as_tree, ast_str, file_path, args):
    loop_nodes = LoopDetector.detect(as_tree)
    if not loop_nodes:
        return ""
    else:
        res = "\n\n"
        for node in loop_nodes:
            res += _format_node(file_path, node)
        res += "Total number of loop/recursive nodes captured: {}\n".format(len(loop_nodes))
    return res + "\n"
