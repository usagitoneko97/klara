import unittest
from textwrap import dedent

from klara.klara_z3.cov_manager import CovManager

from .test_condition_solver import BaseCoverageTest

MANAGER = CovManager()


class TestCoverReturn(BaseCoverageTest):
    def test_replaced_conditions(self):
        test = dedent(
            """\
            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number = self.cfg["number"]
                    self.number_w = self.cfg["number_w"]

                def Top(self):
                    z = 2
                    if self.cm > 1:
                        z = 3
                        if self.number > 5:
                            z = 7
                            if self.number_w > 10:
                                some = 1
                            else:
                                z = 10
                        # phi(z) * 4
                    # phi(z)
                    if self.cm < 1:
                        z = 5
                    # phi(z)
                    return z

        """
        )
        self.run_solver_with_cov(test, 6, expected_return={2, 3, 7, 10, 5})

    def test_replaced_else(self):
        test = dedent(
            """\
            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number = self.cfg["number"]
                    self.number_w = self.cfg["number_w"]

                def Top(self):
                    z = 2
                    if self.cm > 1:
                        if self.number > 5:
                            pass
                        else:
                            z = 12
                            if self.number_w > 10:
                                some = 1
                            else:
                                z = 10
                    if self.cm < 1:
                        z = 5
                    return z

        """
        )
        self.run_solver_with_cov(test, 4, 93, expected_return={2, 12, 10, 5})

    def test_replaced_scope_bound(self):
        test = dedent(
            """\
            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number = self.cfg["number"]
                    self.number_w = self.cfg["number_w"]

                def Top(self):
                    z = 2
                    if self.cm > 1:
                        if self.number > 5:
                            z = 7
                    return z

        """
        )
        self.run_solver_with_cov(test, 2, expected_return={2, 7})

    def test_replaced_same_cond(self):
        test = dedent(
            """\
            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number = self.cfg["number"]
                    self.number_w = self.cfg["number_w"]

                def Top(self):
                    z = 2
                    if self.cm > 1:
                        if self.cm > 1:
                            z = 3
                    return z

        """
        )
        self.run_solver_with_cov(test, 2, expected_return={2, 3})

    def test_replaced_trace_conditions(self):
        test = dedent(
            """\
            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number = self.cfg["number"]
                    self.number_w = self.cfg["number_w"]

                def Top(self):
                    x = 1 if self.number == 54 else 2
                    z = 2
                    if x != 1:
                        if self.cm > 1:
                            z = 3
                    return z

        """
        )
        self.run_solver_with_cov(test, 3, expected_return={2, 3})

    def test_replaced_true_replaced(self):
        test = dedent(
            """\
            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number = self.cfg["number"]
                    self.number_w = self.cfg["number_w"]

                def Top(self):
                    x = 1 if self.number == 54 else 2
                    z = 2
                    z = 4
                    if x == 1:
                        if self.cm > 1:
                            z = 3
                    if self.cm == 156:
                        z = 5
                    else:
                        z = 6
                    return z

        """
        )
        self.run_solver_with_cov(test, 6, 87, expected_return={5, 6})

    @unittest.skip("Implement multi targets")
    def test_replaced_multi_targets(self):
        test = dedent(
            """\
            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number = self.cfg["number"]
                    self.number_w = self.cfg["number_w"]

                def Top(self):
                    x = 1 if self.number == 54 else 2
                    z = 2
                    z = 4
                    if x == 1:
                        if self.cm > 1:
                            z = z + 1
                    if self.cm == 156:
                        z = z + 5
                    If self.number_w == 1623:
                        z = z + 6
                    return z

        """
        )
        self.run_solver_with_cov(test, 6, 87, expected_return={5, 6})

    def test_replaced_not_no_bound(self):
        test = dedent(
            """\
            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number = self.cfg["number"]
                    self.number_w = self.cfg["number_w"]

                def Top(self):
                    x = 1 if self.number == 54 else 2
                    z = 2
                    z = 4
                    if x == 1:
                        z = z + 10
                        if self.cm > 1:
                            z = z + 1
                    if self.cm == 156:
                        z = z + 5
                    if self.number_w == 1623:
                        z = z + 6
                    return z

        """
        )
        # 19 not here because path not(self.cm > 1) will not be sat
        self.run_solver_with_cov(test, 10, expected_return={4, 14, 15, 9, 20, 10, 20, 21, 15, 26})

    def test_replaced_elif(self):
        test = dedent(
            """\
            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number = self.cfg["number"]
                    self.number_w = self.cfg["number_w"]

                def Top(self):
                    z = 2
                    z = 4
                    if self.cm == 1:
                        pass
                    elif self.cm == 156:
                        z = 6
                    elif self.cm == 1623:
                        z = 7
                    else:
                        z = 8
                    return z

        """
        )
        self.run_solver_with_cov(test, 10, 93, expected_return={6, 7, 4, 8})

    def test_replaced_reduced_conds(self):
        test = dedent(
            """\
            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number = self.cfg["number"]
                    self.number_w = self.cfg["number_w"]

                def Top(self):
                    z = 4
                    y = 1
                    if self.cm == 1:
                        z = 5
                        y = 2
                    elif self.cm == 2:
                        z = 6
                        y = 3
                    return z + y

        """
        )
        self.run_solver_with_cov(test, 3, expected_return={5, 7, 9})

    def test_elif_more_than_1_at_else(self):
        test = dedent(
            """\
            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number = self.cfg["number"]
                    self.number_w = self.cfg["number_w"]

                def Top(self):
                    y = 1
                    if self.cm == 1:
                        pass
                    elif self.cm == 2:
                        pass
                    else:
                        y = 2
                    return y

        """
        )
        self.run_solver_with_cov(test, 2, 92, expected_return={1, 2})

    def test_nested_phi(self):
        test = dedent(
            """\
            class MyClass:
                def init(self):
                    self.cm = self.cfg["cm"]
                    self.number = self.cfg["number"]
                    self.number_w = self.cfg["number_w"]
                    self.pp_en = self.cfg["ppen"]
                    self.var1 = self.cfg["var1"]
                    self.re = self.cfg["re"]

                    self.cln = (self.number -1)/55 + 1
                    self.cln = 0
                    self.single_io_num = 0
                    x = 0
                    if(self.pp_en):
                        x = 1
                        self.cln = 3
                        self.var1 = self.var1 + self.re
                    self.number = self.number + self.cln * self.re
                    if(self.number % 2 == 0):
                        self.single_io_num = 2 + x
                    if self.cln == 1:
                        pass
                    elif self.cln == 2:
                        pass
                    elif self.cln == 3:
                        if(self.pp_en):
                            self.number_1lc = self.var1
                        else:
                            self.number_1lc = 3 * 2
                        self.number_remain = self.number - self.number_1lc
                        if(self.pp_en):
                            self.single_io_num = 4      # 3 replaced 2
                            if(self.number_remain != 2):
                                self.single_io_num = 5  # 4
                            x = 1       # 5 = phi(3, 4)  replaced 3
                        x = 2           # 6 = phi(2, 5)  replaced 2
                    x = 3               # 2 6
                def Top(self):
                    return self.single_io_num
        """
        )
        self.run_solver_with_cov(test, 4, 90, expected_return={0, 2, 4, 5})
