import copy
import itertools
from typing import List, Optional

import klara.core.nodes as nodes
import klara.core.use_def_chain as use_def_chain
from klara.core import exceptions, utilities
from klara.core.ssa_visitors import TargetRemover
from . import manager
from .ssa_visitors import AstVisitor

MANAGER = manager.AstManager()


class SsaCode(object):
    def __init__(self, parent_node=None):
        self.code_list = []
        self.parent_node = parent_node

    def __repr__(self):
        s = ""
        for ssa in self.code_list:
            s = s + str(ssa) + "\n"

        return s

    def __iter__(self):
        for ssa in self.code_list:
            yield ssa

    def add_code(self, code, containing_block):
        if code:
            self.code_list.append(code)
            code.refer_to_block = containing_block
            if containing_block.scope is not None:
                assert (
                    containing_block.scope == code.scope().refer_to_block
                ), "code lineno: {} in the same blocks does not refer to the same scope".format(code.lineno)
            else:
                if isinstance(code, nodes.LocalsDictNode):
                    try:
                        containing_block.scope = code.parent.scope().refer_to_block
                    except AttributeError:
                        containing_block.scope = None
                else:
                    containing_block.scope = code.scope().refer_to_block

    def get_all_phi_functions(self):
        for code in self.code_list:
            if code.statement().is_phi:
                yield code

    def get_phi_function(self, var):
        for phi_func in self.get_all_phi_functions():
            if phi_func.value.base_name == str(var):
                return phi_func

    def add_phi_function(self, phi_name, parent_node, block):
        """
        construct ast.Assign class with value=Phi, target=target
        :param phi_name: list of phi values
        :param base_var: the variable that this phi function is based on
        :return: constructed ast.assign stmt
        """
        MANAGER.logger.debug("SSA", "adding a new phi function for lineno: {}", parent_node.lineno)
        ast_node = nodes.Assign(parent=parent_node)
        # phi_name will be the AssignName/AssignAttribute. The phi_ssa_var will only use
        # the structure and change the type to non-assign counterpart
        cls = nodes.Name if isinstance(phi_name, nodes.AssignName) else nodes.Attribute
        phi_ssa_var = cls.quick_build_from_counter_part(phi_name)
        phi_ssa_var.parent = ast_node
        phi_ssa_var.convert_to_ssa()
        phi_assign = copy.copy(phi_name)
        phi_assign.parent = ast_node
        phi_assign.version = -1
        phi_func = nodes.Phi(value=[phi_ssa_var], base_name=str(phi_name))
        ast_node.postinit(targets=[phi_assign], value=phi_func)
        ast_node.refer_to_block = block
        phi_func.parent = ast_node
        self.code_list.insert(0, ast_node)

    def remove_targets_from_var_stack(self, targets):
        for target in targets:
            TargetRemover().visit(target)


def _is_node_subset_of(node, target_node):
    """Check whether node is a subset of target_node"""
    parent = node
    try:
        while True:
            if parent == target_node:
                return True
            parent = parent.parent
    except AttributeError:
        return False


class AttributeEnumerator(AstVisitor):
    def __init__(self, original_node, allow_uninitialized=False, delete_if_uninitialized=True):
        self.original_node = original_node
        # store in order to perform the updating of variable last
        self.var_to_update = []  # type: (List[Optional[nodes.AssignName, nodes.AssignAttribute]])
        self.allow_uninitialized = allow_uninitialized
        self.delete_if_uninitialized = delete_if_uninitialized
        self.__remove_node = False  # internal flag used to remove the node entirely

    @staticmethod
    def enumerate(node, allow_uninitialized=False, delete_if_uninitialized=False):
        c = AttributeEnumerator(node, allow_uninitialized, delete_if_uninitialized)
        c.visit(node)
        if c.__remove_node:
            return None  # return None to remove the node
        for var in c.var_to_update:
            var.convert_to_ssa()
        c.var_to_update[:] = []

    def visit_attribute(self, node):
        self.visit(node.value)
        if not node.value:
            return None  # delete the whole stmt if any of the node is None
        # carry out SSA conversion only if it haven't converted before
        node.convert_to_ssa()
        use_def_chain.link(node)

    def visit_assignattribute(self, node):
        self.visit(node.value)
        if not node.value:
            return None  # delete the whole stmt if any of the node is None
        self.var_to_update.append(node)

    def visit_name(self, node):
        # the first name of the attr
        node.convert_to_ssa()
        use_def_chain.link(node)

    def visit_assignname(self, node):
        self.var_to_update.append(node)

    def visit_subscript(self, node):
        self.generic_visit(node)
        if node.is_load_var():
            node.convert_to_ssa()
        else:
            self.var_to_update.append(node)

    def visit_alias(self, node):
        node.convert_to_ssa()

    def visit_call(self, node: nodes.Call):
        # store the ssa_records and locals up to this point, store the instance into the relevant scope
        # TODO: storing across module. See (#mey0v)
        self.generic_visit(node)
        try:
            instance = node.func.instance()
            scope = node.scope()
            # store scope() locals and instance locals. E.g.
            # >>> f.g() # store scope().locals and f.locals
            node.locals["instance"] = instance.locals.copy()
            node.locals["scope"] = scope.locals.copy()
            node.ssa_record = instance.ssa_record.copy()
        except (exceptions.InstanceNotExistError, NotImplementedError, AttributeError):
            return
        cls_ins = nodes.ClassInstance(node, node.func.get_stmt_target())
        try:
            for ins in node.get_target_instance():
                ins.instance_dict[node] = cls_ins
        except (exceptions.InstanceNotExistError, AttributeError):
            pass
        # get the kill info for the resolved func/method. Initialize KillVarCall if it exist
        cls_ins.resolve_instance(resolve_constructor=True)
        if len(cls_ins.global_var) > 0:
            for global_var, scope in cls_ins.global_var.items():
                global_var = list(global_var)
                arg = cls_ins.target_cls.args.get_caller_arg(global_var[0], node)
                vars = []
                stmt = nodes.Assign(node.lineno, node.col_offset, node.parent)
                kill_var_call = nodes.KillVarCall(node.lineno, node.col_offset, node.parent)
                for n in itertools.chain(arg, (global_var[0],)):
                    if arg:
                        global_var[0] = n
                    var = nodes.Variable.build_var(
                        global_var, assigned=True, lineno=node.lineno, col_offset=node.col_offset, parent=stmt
                    )
                    # rename the variable to reflect it will be change in the func
                    self.visit(var)
                    vars.append(var)
                # build a statement
                kill_var_call.postinit(var=global_var[-1], value=node, scope=scope)
                stmt.postinit(vars, kill_var_call)

    def visit_phi(self, node: nodes.Phi):
        """
        for each node, get the linked's statement's replaced_links that contain assignName,
        check with phi's value for that assignName
        """
        self.generic_visit(node)
        # remove redundant phi values (same version number)
        versions = set()
        final_value = []
        for value in node.value:
            if value.version == -1 or value.version not in versions:
                final_value.append(value)
                versions.add(value.version)
                if value.links:
                    stmt = value.links.statement()
                    for replaced_name in stmt.get_all_replaced_links():
                        replaced_phis_values = list(
                            filter(lambda x: utilities.compare_variable(x, replaced_name), node.value)
                        )
                        if len(replaced_phis_values) > 0:
                            if len(replaced_phis_values) > 1:
                                MANAGER.logger.warning(
                                    "SSA",
                                    "ssa variable: {} should not match more than one. Matched: {]",
                                    replaced_name,
                                    replaced_phis_values,
                                )
                            node.replaced_map.setdefault(value, []).append(replaced_phis_values[0])
            else:
                MANAGER.logger.info("SSA", "Skipping phi node: {} of stmt: {} at line: {}", value, node, node.lineno)
        node.value = final_value
