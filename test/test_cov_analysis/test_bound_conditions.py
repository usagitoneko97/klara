from textwrap import dedent

from klara.klara_z3.cov_manager import CovManager

from ..helper.base_test import BaseTestInference

MANAGER = CovManager()


class TestBoundCondition(BaseTestInference):
    @staticmethod
    def assert_bound_conditions(infer_stmt, bound_conditions: dict):
        for stmt_name, expected_conditions in bound_conditions.items():
            real_bound_conditions = []
            expected_conditions = [sorted(map(str, cond)) for cond in expected_conditions]
            stmt = getattr(infer_stmt, stmt_name, None)
            if not stmt:
                raise ValueError("statement named: {} not found in ast string".format(stmt_name))
            for result in stmt.infer():
                real_bound_conditions.append(sorted(map(str, result.bound_conditions)))
            assert sorted(real_bound_conditions) == sorted(expected_conditions)

    def test_if_else(self):
        statement, _ = self.build_tree_cfg(
            dedent(
                """\
                if x > 1:
                    if y < 3:
                        z = 3   #@ bound_2 (value)
                elif x < -2:
                    z = 3   #@ else_bound (value)
             """
            )
        )
        self.assert_bound_conditions(
            statement, {"bound_2": [{"y < 3", "x > 1"}], "else_bound": [{"not(x > 1)", "x < -(2)"}]}
        )

    def test_phi(self):
        statement, _ = self.build_tree_cfg(
            dedent(
                """\
                if x > 1:
                    if y < 3:
                        z = 3
                    else:
                        z = 6
                elif x < -2:
                    z = 5
                else:
                    z = 9
                
                y = z   #@ phi_bound (value)
             """
            )
        )
        self.assert_bound_conditions(
            statement,
            {
                "phi_bound": [
                    {"y < 3", "x > 1"},
                    {"x > 1", "not(y < 3)"},
                    {"not(x > 1)", "x < -(2)"},
                    {"not(x > 1)", "not(x < -(2))"},
                ]
            },
        )

    def test_list_bound_conditions(self):
        statement, _ = self.build_tree_cfg(
            dedent(
                """\
                if x > 1:
                    if y < 3:
                        z = 3
                    else:
                        z = 6
                elif x < -2:
                    z = 5
                else:
                    z = 9
                s = [z, z, 1, 2, 4]
                y = s * 0   #@ phi_bound (value)
             """
            )
        )
        self.assert_bound_conditions(statement, {"phi_bound": [[]]})

    def test_list_bound_conditions_2(self):
        statement, _ = self.build_tree_cfg(
            dedent(
                """\
                if x > 1:
                    z = 3
                else:
                    z = 9
                if r >= 10:
                    op = 0
                else:
                    op = 1
                s = [z, z, 1, 2, 4]
                y = s * op   #@ phi_bound (value)
             """
            )
        )
        self.assert_bound_conditions(
            statement, {"phi_bound": [{"r >= 10"}, {"not(r >= 10)", "x > 1"}, {"not(r >= 10)", "not(x > 1)"}]}
        )

    def test_binop(self):
        statement, _ = self.build_tree_cfg(
            dedent(
                """\
                if x > 1:
                    z = 3
                else:
                    z = 9
                if r >= 10:
                    op = 0
                else:
                    op = 1
                y = z +op   #@ phi_bound (value)
             """
            )
        )
        self.assert_bound_conditions(
            statement,
            {
                "phi_bound": [
                    {"r >= 10", "x > 1"},
                    {"not(r >= 10)", "x > 1"},
                    {"not(x > 1)", "r >= 10"},
                    {"not(r >= 10)", "not(x > 1)"},
                ]
            },
        )
