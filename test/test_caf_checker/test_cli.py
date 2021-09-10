import unittest
from textwrap import dedent

from klara.core.manager import AstManager

from ..helper.base_test import BaseTestCli


class TestCli(BaseTestCli):
    def test_default(self):
        with self.assertRaises(SystemExit) as e:
            self.run_fcf_with_arg(["-h"])
        assert type(e.exception) is SystemExit

    def test_multiple_files(self):
        f = self.makepyfile(
            mod_1=dedent(
                """\
            x = 1.5
            x == 1
            """
            )
        )
        g = self.makepyfile(
            mod_2=dedent(
                """\
            y = 1.5
            y == 1
            """
            )
        )
        result = self.run_fcf_with_arg([str(f), str(g)])
        assert (
            dedent(
                """\
            line: 2
            x == 1
            ^
            x = 1.5 (<class 'float'>)"""
            )
            in result
        )

    def test_config_file(self):
        f = self.makepyfile(
            mod_1=dedent(
                """\
                def foo():
                    1 == 1.5
                x = 1.5
                x > 1
                x == 1
                """
            )
        )
        config_f = self.makefile(
            fcf=dedent(
                """\
            eq-neq = True
            no-analyze-procedure = True
        """
            ),
            ext="ini",
        )
        result = self.run_fcf_with_arg([str(f), "-c", str(config_f)])
        print(result)
        assert "Total number of floating-point warnings captured: 1" in result

    @unittest.skip("skip temporary to solve test dependency issue")
    def test_extension_loading(self):
        ext = self.makepyfile(
            ext1=dedent(
                """\
                from klara.core import inference, manager, nodes
                MANAGER = manager.AstManager()


                def check_bin_op(node):
                    # return only right operand is 4
                    if isinstance(node.right, nodes.Const):
                        return node.right.value == 4
                    return False


                def infer_binop(node, context=None):
                    # custom bin op inference here
                    yield inference.InferenceResult.load_result(nodes.Const(100.1))


                MANAGER.register_transform(nodes.BinOp, inference.inference_transform_wrapper(infer_binop),
                                           check_bin_op)
            """
            )
        )
        af = self.makepyfile(
            af=dedent(
                """\
                x = 1
                y = x + 2
                z = y - 4   # will infer as 100.1
                z == 1
            """
            )
        )
        self.force_initialize()
        result = self.run_fcf_with_arg([str(af), "--infer-extension", str(ext), "-v"])
        expected_extension = {"builtin_inference.py", "ext1.py", "typeshed_stub.py"}
        for s in expected_extension:
            assert s in result
        assert (
            dedent(
                """\
                    line: 4
                    z == 1
                    ^
                    z = 100.1 (<class 'float'>)

                    Total number of floating-point warnings captured: 1
                """
            )
            in result
        )
        AstManager().transform.transform_cache.clear()

    @unittest.skip("skip temporary to solve test dependency issue")
    def test_2prm_loading(self):
        ext1 = self.makefile(
            ext1=dedent(
                """\
        <?xml version="1.0" encoding="UTF-8"?>
        <!--prm version="1.0"-->
        <param_list description="base-level xxx">
            <parameter
                    name="var1"
                    type="INT"
                    description="another"
                    comment="another comment"
                    level_edit="LAJD:LKJ"
                    parameter_group="SOME_OPTIONS"
            />
            <parameter
                    name="top"
                    type="REAL"
                    description="another"
                    comment="another comment"
                    level_edit="LAJD:LKJ"
                    parameter_group="SOME_OPTIONS"
            />
        </param_list>
        """
            ),
            ext="prm",
        )
        ext2 = self.makefile(
            ext2=dedent(
                """\
        <?xml version="1.0" encoding="UTF-8"?>
        <!--prm version="1.0"-->
        <param_list description="base-level xxx">
            <parameter
                    name="var1"
                    type="INT"
                    description="another"
                    comment="another comment"
                    level_edit="LAJD:LKJ"
                    parameter_group="SOME_OPTIONS"
            />
            <parameter
                    name="bottom"
                    type="REAL"
                    description="another"
                    comment="another comment"
                    level_edit="LAJD:LKJ"
                    parameter_group="SOME_OPTIONS"
            />
        </param_list>
        """
            ),
            ext="prm",
        )
        af = self.makepyfile(
            af=dedent(
                """\
            class F:
                def foo(self):
                    x = self.cfg["var1"]
                    z = x / 4 % 8   # python2 will evaluate to int
                    z == 1
                    y = self.cfg["invalid"]
                    y == 1
                    self.cfg["top"] == self.cfg["bottom"]
        """
            )
        )
        result = self.run_fcf_with_arg(["--prm-data", str(ext1), str(ext2), "-py", "2", str(af)])
        assert (
            dedent(
                """\
        In foo
        line: 8
        self.cfg["top"] == self.cfg["bottom"]
        ^                  ^
        self.cfg['top'] = Unknown value (<class 'float'>)
        self.cfg['bottom'] = Unknown value (<class 'float'>)
        """
            )
            in result
        )
        assert "Total number of floating-point warnings captured: 1" in result

    def test_no_analyze_procedure(self):
        af = self.makepyfile(
            af=dedent(
                """\
                def some():
                    1 == 1.5
        """
            )
        )
        result = self.run_fcf_with_arg([str(af), "--no-analyze-procedure"])
        assert result == ""
