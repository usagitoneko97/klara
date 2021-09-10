from klara.core import config, manager
from test.helper.base_test import BaseTestInference


class TestTypeInference(BaseTestInference):
    def test_simple_name(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            def foo(x: int):
                y = x
        """
        )
        result = list(as_tree.body[0].body[0].targets[0].infer())
        assert result[0].result_type.name == "int"

    def test_phi_values(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            def foo(x: int, y: float):
                if True:
                    z = x
                else:
                    z = y
                f = z   # f could be int or float
        """
        )
        result = list(as_tree.body[0].body[-1].targets[0].infer())
        assert result[0].result_type.name == "int"
        assert result[1].result_type.name == "float"

    def test_func_call(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            def fee(x: int, y: float):
                def foo(x, y):
                    return x / y
                z = foo(x, y)
        """
        )
        result = list(as_tree.body[0].body[1].targets[0].infer())
        assert result[0].result_type.name == "float"

    def test_type_inference_list(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            def foo(x: int):
                y = x + 1
                z = y / 1
                f = y < z
                lst = [x, y, f]
                lst_elem = lst[0]
                lst_elem = lst[2]
        """
        )
        result = list(as_tree.body[0].body[0].targets[0].infer())
        assert result[0].result_type.name == "int"
        result = list(as_tree.body[0].body[1].targets[0].infer())
        assert result[0].result_type.name == "float"
        result = list(as_tree.body[0].body[2].targets[0].infer())
        assert result[0].result_type.name == "bool"
        # FIXME: add type inference for uninferable item in sequence
        # result = list(as_tree.body[0].body[4].targets[0].infer())
        # assert result[0].result_type.name == "int"
        # result = list(as_tree.body[0].body[5].targets[0].infer())
        # assert result[0].result_type.name == "bool"

    def test_compare_dunder(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Foo():
                def __init__(self):
                    pass
                def __eq__(self, other) -> int:
                    return 4 + other

            f = Foo()
            z = f == 1  # 4 + 1
        """
        )
        result = list(as_tree.body[-1].targets[0].infer())
        assert result[0].result.value == 5
        assert result[0].result_type.name == "int"

    def test_int_class_method(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            value = 1
            value.bit_length()  # int
            value.conjugate()   # int
        """
        )
        result = list(as_tree.body[1].value.infer())
        assert result[0].result_type.name == "int"
        result = list(as_tree.body[2].value.infer())
        assert result[0].result_type.name == "int"

    def test_str_class_method(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            value = "this is a sample string"
            value.capitalize()  # str
            value.isalpha()    # bool
            value.count()       # int
        """
        )
        result = list(as_tree.body[1].value.infer())
        assert result[0].result_type.name == "str"
        result = list(as_tree.body[2].value.infer())
        assert result[0].result_type.name == "bool"
        result = list(as_tree.body[3].value.infer())
        assert result[0].result_type.name == "int"

    def test_builtin_not_covered_by_extension(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            z = all(x, y)
        """
        )
        result = list(as_tree.body[-1].value.infer())
        assert result[0].result_type.name == "bool"


class TestPep484(BaseTestInference):
    @classmethod
    def setUpClass(cls):
        man = manager.AstManager()
        man.initialize(config.Config())

    @classmethod
    def tearDownClass(cls) -> None:
        """don't tear down super"""

    def test_simple_aliasing(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            S = int
            def foo(x: S):
                y = x
        """
        )
        result = list(as_tree.body[1].body[0].targets[0].infer())
        assert result[0].result_type.name == "int"
