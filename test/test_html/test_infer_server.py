from textwrap import dedent

from klara.core import manager, utilities
from klara.html import report
from klara.scripts.py_check import config
from test.helper import base_test

MANAGER = manager.AstManager()


class TestInferServer(base_test.BaseTestInference):
    def xtest_infer_simple(self):
        args = config.ConfigNamespace()
        with utilities.temp_config(MANAGER, args):
            ast_str = dedent(
                """\
                        z = 3
                        x = z * 4.5
                        x = x + 1
                        if z >= 6:     # will not flag
                            y = 60
                        elif x != 1:   # will flag
                            y = 2.5
                        else:
                            y = 3
                            if (x + 5) == 867:   # will flag
                                x = 987
                                k = y == 90   # will not flag
                        z = y == (z != 1.5)   # will flag twice
                            """
            )
            tree, _ = self.build_tree_cfg(ast_str)
            hr = report.HtmlReporter("", ast_str, None, tree)
            list(hr.tokenize_source())
            result = list(hr.infer(3, 4))
            pass
