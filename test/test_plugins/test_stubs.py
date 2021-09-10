import pathlib
from textwrap import dedent

from klara.core.manager import AstManager
from test.helper.base_test import BaseTestInference

MANAGER = AstManager()


class TestTypeShed(BaseTestInference):
    def test_math(self):
        config = self.setup_fcf_config(overwrite=True, typeshed_select=["math"])
        self.force_initialize(config, smt_disable=True)
        as_tree, _ = self.build_tree_cfg(
            """\
            import math
            s = math.cos(23)    # float
        """
        )
        result = [val.result_type.name for val in as_tree.body[1].targets[0].infer()]
        assert result == ["float"]

    def test_typeshed_all(self):
        config = self.setup_fcf_config(overwrite=True, typeshed_select=["ALL"])
        self.force_initialize(config, smt_disable=True)
        as_tree, _ = self.build_tree_cfg(
            """\
            import math
            s = math.cos(23)    # float
        """
        )
        result = [val.result_type.name for val in as_tree.body[1].targets[0].infer()]
        assert result == ["float"]


class TestStubs(BaseTestInference):
    def test_stub1(self):
        example_stub = pathlib.Path(__file__).parent / "example_stub.pyi"
        with example_stub.open("r") as f:
            config = self.setup_fcf_config(overwrite=True, stubs=[f])
            self.force_initialize(config, smt_disable=True)
            as_tree, _ = self.build_tree_cfg(
                """\
                import example_stub
                s = example_stub.Example().foo()
                z = example_stub.Example().attr
                i = example_stub.Example().int_attr
            """
            )
            result = [val.result_type.name for val in as_tree.body[-1].targets[0].infer()]
            assert result == ["int"]
            result = [val.result.value for val in as_tree.body[-2].targets[0].infer()]
            assert result == ["2"]
            result = [val.result_type.name for val in as_tree.body[-3].targets[0].infer()]
            assert result == ["float"]

    def test_sys_version(self):
        example_pyi = self.makefile(
            "pyi",
            example=dedent(
                """\
            if sys.version_info >= (3,):
                def add(x, y) -> float: ...
            else:
                def add(x, y) -> int: ...
        """
            ),
        )
        config = self.setup_fcf_config(overwrite=True, stubs=[example_pyi], py_version=2)
        self.force_initialize(config, smt_disable=True)
        as_tree, _ = self.build_tree_cfg(
            """\
            import example
            f = example.add(1, 2)   # float
        """,
            py2=True,
        )
        result = [val.result_type.name for val in as_tree.body[-1].targets[0].infer()]
        assert result[0] == "int"

    def test_property(self):
        example_pyi = self.makefile(
            "pyi",
            example=dedent(
                """\
            class Foo:
                @property
                def return_int(self, x: int) -> int: ...
                @property
                def return_float(self, x) -> float: ...
        """
            ),
        )
        config = self.setup_fcf_config(overwrite=True, stubs=[example_pyi])
        self.force_initialize(config, smt_disable=True)
        as_tree, _ = self.build_tree_cfg(
            """\
            import example
            f = example.Foo()
            z = f.return_int + f.return_float
        """
        )
        result = [val.result_type.name for val in as_tree.body[-1].targets[0].infer()]
        assert result[0] == "float"

    def test_overload(self):
        example_pyi = self.makefile(
            "pyi",
            example=dedent(
                """\
            class Example:
                @overload
                def ret_val(self, x: int) -> float: ...
                @overload
                def ret_val(self, x: float) -> int: ...
            @overload
            def custom_add(x: str) -> float: ...
            @overload
            def custom_add(x: int) -> int: ...
        """
            ),
        )
        config = self.setup_fcf_config(overwrite=True, stubs=[example_pyi])
        self.force_initialize(config, smt_disable=True)
        as_tree, _ = self.build_tree_cfg(
            """\
            import example
            float_val = example.Example().ret_val(2)
            int_val = example.Example().ret_val(2.1)
            _ = example.custom_add("s")
        """
        )
        result = [val.result_type.name for val in as_tree.body[1].targets[0].infer()]
        assert result[0] == "float"
        result = [val.result_type.name for val in as_tree.body[2].targets[0].infer()]
        assert result[0] == "int"
        result = [val.result_type.name for val in as_tree.body[3].targets[0].infer()]
        assert result[0] == "float"

    def test_invalid_type(self):
        example_pyi = self.makefile(
            "pyi",
            example=dedent(
                """\
            from typing import TypeVar
            ST = TypeVar()
            OT = TypeVar()
            @overload
            def ret_val(x: ST) -> float: ...
            @overload
            def ret_val(x: OT) -> int: ...
        """
            ),
        )
        config = self.setup_fcf_config(overwrite=True, stubs=[example_pyi])
        self.force_initialize(config, smt_disable=True)
        as_tree, _ = self.build_tree_cfg(
            """\
            import example
            float_val = example.ret_val(2)
        """
        )
        result = [val.result_type.name for val in as_tree.body[1].targets[0].infer()]
        assert result[0] == "int"
