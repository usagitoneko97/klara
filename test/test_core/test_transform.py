import ast
import contextlib

from klara.core import inference, manager, nodes
from klara.core.inference import InferenceResult, inference_transform_wrapper
from klara.core.tree_rewriter import TreeRewriter
from test.helper.base_test import BaseTestInference

MANAGER = manager.AstManager()


@contextlib.contextmanager
def add_transform(manager, node, transform, predicate=None):
    manager.register_transform(node, transform, predicate)
    yield
    manager.unregister_transform(node, transform, predicate)


class TestCustomTransform:
    def test_no_predicate(self):
        """change x = 1 to y = 1"""

        def transform_assignname(node):
            node.id = "y"
            return node

        as_tree = ast.parse("x = 1")
        with add_transform(MANAGER, nodes.AssignName, transform_assignname):
            new_tree = TreeRewriter().visit_module(as_tree)
            MANAGER.apply_transform(new_tree)
            assert new_tree.body[0].targets[0].id == "y"

    def test_with_predicate(self):
        """change x = 1 to y = 1"""

        def check_name(node):
            return node.id == "a"

        def transform_name(node):
            node.id = "y"
            return node

        as_tree = ast.parse("x = y + z + a")
        with add_transform(MANAGER, nodes.Name, transform_name, check_name):
            new_tree = TreeRewriter().visit_module(as_tree)
            MANAGER.apply_transform(new_tree)
            assert repr(new_tree.body[0].value) == "BinOp: BinOp: y + z + y"


class TestExplicitInference(BaseTestInference):
    def test_explicit_inference(self):
        def check_bin_op(node):
            if isinstance(node.right, nodes.Const):
                return node.right.value == 4
            return False

        def infer_binop(node, context=None):
            # custom bin op inference here
            yield InferenceResult.load_result(nodes.Const(4))

        with add_transform(MANAGER, nodes.BinOp, inference_transform_wrapper(infer_binop), check_bin_op):
            as_tree, _ = self.build_tree_cfg(
                """\
                x = 1
                y = x + 2
                z = y - 4
            """
            )
            result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
            assert result == [4]

    def test_use_inference_default(self):
        def check_bin_op(node):
            if isinstance(node.right, nodes.Const):
                return node.right.value == 4
            return False

        def infer_binop(node, context=None):
            # custom bin op inference here
            raise inference.UseInferenceDefault()
            # convert to iterator function
            yield

        with add_transform(MANAGER, nodes.BinOp, inference_transform_wrapper(infer_binop), check_bin_op):
            as_tree, _ = self.build_tree_cfg(
                """\
            x = 1
            y = x + 2
            z = y - 4
        """
            )
            result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
            assert result == [-1]
