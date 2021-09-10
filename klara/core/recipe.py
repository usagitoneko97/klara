from . import context_mod, nodes, ssa_visitors


class ClassInstanceBuilder(ssa_visitors.AstVisitor):
    """
    build the class instance from constructor, attribute etc... and load it
    in all `self` arg.
    """

    def __init__(self):
        self.context = context_mod.InferenceContext()
        self.class_ins = nodes.ClassInstance()

    def visit_classdef(self, node: nodes.ClassDef):
        # construct an instance and load context
        # load the locals of the class (class level attribute) and the constructor
        self.class_ins.merge_class_complete(self.context, node, resolve_constructor=True)
        # map all `self` arg of bound method to the created instance. (i.e. to bound
        # the instance)
        for func_body in node.body:
            if isinstance(func_body, nodes.FunctionDef) and func_body.type == "method":
                self.context.map_args_to_func(self.class_ins, func_node=func_body)
        self.generic_visit(node)
