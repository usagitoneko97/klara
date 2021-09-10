from klara.core import config
from klara.core.manager import AstManager
from test.helper.base_test import BaseTestInference

MANAGER = AstManager()


class TestBuiltins(BaseTestInference):
    @classmethod
    def setUpClass(cls):
        MANAGER.initialize(config.Config())

    @classmethod
    def tearDownClass(cls) -> None:
        """don't tear down super"""

    def test_abs(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                _ = abs(-1)
                _ = abs(1)
                _ = abs(-1.5)

                class F:
                    def __init__(self, x):
                        self.x = x
                    def __abs__(self):
                        return abs(self.x) + 2
                f = F(-1.6)
                z = abs(f)
                def foo(x: int):
                    z = abs(x)
            """
        )
        result = [[val.result.value for val in body.targets[0].infer()] for body in as_tree.body[:3]]
        assert result == [[1], [1], [1.5]]
        instance_result = [val.result.value for val in as_tree.body[-2].targets[0].infer()]
        assert instance_result == [3.6]
        instance_result = [val for val in as_tree.body[-1].body[0].targets[0].infer()]
        assert instance_result[0].result_type.name == "int"

    def test_int(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                s = int(1) + int(1.5)
                z = int(-1.5) / int(5.888)

                class F:
                    def __init__(self, x):
                        self.x = x
                    def __int__(self):
                        return int(self.x) + 2
                f = F(-6.555)
                z = int(f)
                def foo(x: float):
                    z = int(x)
                default = int()
            """
        )
        result = [[val.result.value for val in body.targets[0].infer()] for body in as_tree.body[:2]]
        assert result == [[2], [-0.2]]
        instance_result = [val.result.value for val in as_tree.body[-3].targets[0].infer()]
        assert instance_result == [-4]
        instance_result = [val for val in as_tree.body[-2].body[0].targets[0].infer()]
        assert instance_result[0].result_type.name == "int"
        default = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert default == [0]

    def test_float(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                s = float('1e-003') + float('+1E3')
                z = float()
            """
        )
        result = [[val.result.value for val in body.targets[0].infer()] for body in as_tree.body[:2]]
        assert result == [[1000.001], [0.0]]

    def test_str(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                s = str(1.5555)
                z = str({1: 2, 3: 4})
                g = str()
            """
        )
        result = [[val.result.value for val in body.targets[0].infer()] for body in as_tree.body[:3]]
        assert result == [["1.5555"], ["{1: 2, 3: 4}"], [""]]

    def test_len(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                d = {1: 2, 3: 4}
                s = len('some') + len([1, 2, 3]) + len((1, 2, 3)) + len({2, 3, 4}) + len(d)
            """
        )
        result = [val.result.value for val in as_tree.body[1].targets[0].infer()]
        assert result == [15]

    def test_round(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                n = 1.523
                z = round(n, 2)

                class F:
                    def __round__(self, ndigits=2):
                        return ndigits * 2
                f = F()
                two_val = round(f, 2)
                result = two_val + z

                def foo(unknown: int, flt: float):
                    i = round(unknown, 3)   # yield type int
                    z = round(flt, 3)     # yield type float
            """
        )
        result = [val.result.value for val in as_tree.body[-2].targets[0].infer()]
        assert result == [5.52]
        result = [val for val in as_tree.body[-1].body[0].targets[0].infer()]
        assert result[0].result_type.name == "int"
        result = [val for val in as_tree.body[-1].body[1].targets[0].infer()]
        assert result[0].result_type.name == "float"

    def test_round_py2(self):
        self.setup_fcf_config(overwrite=True, py_version=2)
        as_tree, _ = self.build_tree_cfg(
            """\
                round(1)       # float
                round(1.0, 4)  # float
                round(1, None) # float

                def foo(x):
                    round(x)
                    round(x, 4)
            """,
            py2=True,
        )
        result = [[val.result_type.name for val in b.value.infer()] for b in as_tree.body[-1].body[:2]]
        assert result == [["float"], ["float"]]

    def test_infer_unimplemented_builtin(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                z = object(f)
        """
        )
        _ = [r.result for r in as_tree.body[0].targets[0].infer()]
