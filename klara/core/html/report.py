from klara.html import report
from klara.core import manager, nodes, ssa_visitors

MANAGER = manager.AstManager()


class InferHtmlReport(report.HtmlReporter):
    def infer(self, lineno: int, col_offset: int, context=None):
        """Try to infer node at lineno:col_offset
        1. find the node at given lineno:col, if the node can't be find, return some warning
        2. Call infer on the node, get the inference result.
        3. get all id on inference result's infer path

        Response format:
        - "inference_result"
            <list>
                -> "result"
                    -> [result]
                -> "path"
                    -> [path]
                -> "bound_conditions"
                    -> [bound conditions]
                -> "result_type"
                    -> [type] (str)
        - "status"
        """
        nf = ssa_visitors.NodeFinder(lambda x: x.lineno == lineno and x.col_offset == col_offset)
        node = nf.execute(self.tree)
        infer_path_results = {}
        context.path.clear()
        if node:
            MANAGER.logger.info("HTML", "Analyzing node: {} at lineno: {}", node, node.lineno)
            infer_path_results["status"] = 200
            # don't return multiple result that is the same
            result_cache = set()
            for result in node.infer(context):
                result_type = result.result_type.name if result.result_type else ""
                path = self.process_infer_path(result.infer_path)
                frozen_path = frozenset(path)
                curr_hash = hash((frozen_path, str(result), str(result_type)))
                bound_conditions = "\n".join(str(c) for c in result.bound_conditions) if result.bound_conditions else ""
                if curr_hash not in result_cache:
                    result_cache.add(curr_hash)
                    _infer_path_result = {
                        "path": path,
                        "result": str(result),
                        "result_type": str(result_type),
                        "bound_conditions": bound_conditions,
                    }
                    infer_path_results.setdefault("inference_result", []).append(_infer_path_result)
        else:
            infer_path_results["status"] = 500
            MANAGER.logger.warning("HTML", "can't find node in line: {} at col: {}", lineno, col_offset)
        return infer_path_results

    def process_infer_path(self, infer_path):
        result = {}
        for path in infer_path:
            ids = []
            tokens = self.lineno_cache[path.lineno]
            endcol = path.col_offset + (len(str(path)) - 1)
            for token in tokens:
                if path.col_offset <= token.scol <= endcol and token.cls != "ws":
                    ids.append(token.id)
            result[path.lineno] = {"ids": ids, "value": str(path)}
        return result
