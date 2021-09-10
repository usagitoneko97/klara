"""Integrate z3 solver to the inference system"""
import functools
import itertools

from klara.core import context_mod, nodes, utilities, inference
from .cov_manager import CovManager

MANAGER = CovManager()


def expand_condition(expr, context):
    """
    fully yield all possible paths of the condition "expr".
    """
    paths = set()
    for val in expr.infer(context):
        paths.add(val)
        if val.bound_conditions:
            for result in itertools.product(
                *(expand_condition(bound_cond, context) for bound_cond in val.bound_conditions)
            ):
                total = set()
                for r in result:
                    total |= r
                yield paths | total
        else:
            yield paths
        paths = set()


def evaluate_paths(conditions, z3_assumptions, context, inverted_conds=None):
    if len(conditions) == 0:
        yield z3_assumptions, {}
        return
    elif len(conditions) == 1:
        top_bool_node = list(conditions)[0]
    else:
        top_bool_node = nodes.BoolOp()
        top_bool_node.postinit("and", list(conditions))
    inverted_conds = inverted_conds or set()
    if context:
        backup_cond = context.inverted_conds
        backup_conditions_mode = context.conditions_mode
        context.inverted_conds = context.inverted_conds | inverted_conds | conditions
        context.conditions_mode = context_mod.ConditionsMode.IN_PROGRESS
    MANAGER.add_weak_ref(top_bool_node)
    MANAGER.apply_transform(top_bool_node)
    yielded = False
    results = []
    for val_paths in expand_condition(top_bool_node, context):
        # accumulate the selected operand when evaluating bound conditions
        # since the caller will construct a new InferenceResult
        total_selected_operand = {}
        assumptions = set()
        if utilities.check_selected_operand(val_paths):
            yielded = True
            for val in val_paths:
                if val.status:
                    assumptions |= MANAGER.add_conditions({utilities.strip_constant_node(val.result)})
                assumptions |= val.z3_assumptions
                total_selected_operand.update(val.selected_operand)
        else:
            continue
        results.append(((assumptions | z3_assumptions), total_selected_operand))
    if not yielded:
        results.append(((z3_assumptions), {}))
    if context:
        context.inverted_conds = backup_cond
        context.conditions_mode = backup_conditions_mode
    yield from results


def result_check_sat(self, context):
    self.bound_conditions -= context.inverted_conds
    for assumptions, selected_operand in evaluate_paths(
        self.bound_conditions, self.z3_assumptions, context, self.inverted_conditions
    ):
        z3_result = MANAGER.check_assumptions_and_get_model(assumptions)
        if utilities.check_selected_operand((self, selected_operand)):
            yield z3_result, selected_operand


def result_expand(self, context, z3_result):
    context.model = z3_result.model
    old_no_cache = context.no_cache
    old_conditions_mode = context.conditions_mode
    context.no_cache = True
    context.z3_model_used = {}
    context.conditions_mode = context_mod.ConditionsMode.DISABLE
    context.z3_result_hash = z3_result.hash
    expanded_res = list(self.result.infer_expand(context))
    context.no_cache = old_no_cache
    context.model = None
    context.conditions_mode = old_conditions_mode
    if len(expanded_res) > 0:
        expanded_res = expanded_res[0]
        if isinstance(expanded_res.result, nodes.Uninferable):
            return self
        else:
            expanded_res += self
            return expanded_res
    else:
        return self


def infer_expand(node, context):
    item_hash = hash((node, context.z3_result_hash))
    if item_hash in MANAGER.infer_cache:
        results = MANAGER.infer_cache[item_hash]
        if type(results) is tuple:
            context.z3_model_used = results[1]
            yield from results[0]
            return
    results = list(node._infer(context))
    MANAGER.infer_cache[item_hash] = (results, context.z3_model_used.copy())
    yield from results


def infer_check_sat(func):
    """
    wrap `infer` to filter unsat inference result
    """

    @functools.wraps(func)
    def wrapper(node, context=None, *args, **kwargs):
        args_res = list(func(node, context, *args, **kwargs))
        len_after = 0
        cache = {}
        if context.conditions_mode != context_mod.ConditionsMode.DISABLE:
            for res in args_res:
                for z3_result, selected_operand in res.check_sat(context):
                    if z3_result.sat:
                        if not z3_result.assumptions:
                            len_after += 1
                            yield res
                        else:
                            other_res = inference.InferenceResult.from_other(res, selected_operand=selected_operand)
                            other_res.bound_conditions.clear()
                            other_res.z3_assumptions |= z3_result.assumptions
                            yield other_res
            it = (inference.MultiInferenceResult.combine_inference_results(value) for value in cache.values())
        else:
            it = args_res
        if MANAGER.config.max_inference_value is not None and MANAGER.config.max_inference_value > 0:
            it = itertools.islice(it, MANAGER.config.max_inference_value)
        yield from it

    wrapper.wrapped_check_sat = True
    return wrapper


def enable() -> None:
    """Enable z3 solver support for inference system
    All inference result will check by solver for satisfiability, and unsat result are filtered
    :return:  None
    """
    inference.InferenceResult.check_sat = result_check_sat
    inference.InferenceResult.expand = result_expand
    nodes.BaseNode.infer_expand = infer_expand
    MANAGER.enable_infer_check_sat(infer_check_sat)


def disable():
    """Disable z3 solver for inference"""
    MANAGER.disable_infer_check_sat()
