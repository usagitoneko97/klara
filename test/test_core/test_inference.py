import unittest

from klara.core import context_mod, exceptions, inference, nodes, protocols
from klara.core.manager import AstManager
from test.helper.base_test import BaseTestInference

MANAGER = AstManager()


def USE(s):
    pass


USE(inference)
USE(protocols)


class TestInferenceIntra(BaseTestInference):
    def test_single_name(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            x = 1
            y = x
        """
        )
        result = [val.result.value for val in as_tree.body[1].targets[0].infer()]
        assert result == [1]

    def test_unary_op(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            x = -1
            y = x + 3
            f = True
            z = not f
        """
        )
        result = [val.result.value for val in as_tree.body[1].targets[0].infer()]
        assert result == [2]
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [False]

    def test_multiple_names(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            x = 1
            y = x + 3
            z = x + y - x
        """
        )
        result = [val.result.value for val in as_tree.body[2].targets[0].infer()]
        assert result == [4]

    def test_multiple_assign_name(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            x = y = 1 + 4
            z = f = x * y
            f
            z
        """
        )
        result = [val.result.value for val in as_tree.body[-2].value.infer()]
        assert result == [25]
        result = [val.result.value for val in as_tree.body[-1].value.infer()]
        assert result == [25]

    def test_nameconstant_binary_op(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                z = (True | False) & False
        """
        )
        res = [r.result.value for r in as_tree.body[0].targets[0].infer()]
        assert res[0] is False

    def test_binop_with_0(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                a = 0
                a += 1
                a += 3
                z = a   #@ s(value)
        """
        )
        res = [r.result.value for r in as_tree.s.infer()]
        assert res[0] == 4

    def test_bool_op_const(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                True or False
                3 or False      # 3
                0 and 1 and 2   # 0
                1 and 2 and 3
                (0 or 0 or 2) and 0
                2 and 2 and None
        """
        )
        res = [[r.result.value for r in b.value.infer()] for b in as_tree.body]
        assert res == [[True], [3], [0], [3], [0], [None]]

    def test_bool_obj(self):
        """boolean operation with basic class obj"""
        as_tree, _ = self.build_tree_cfg(
            """\
                class C:
                    pass
                c = C()
                0 or c
                c and 0
        """
        )
        res = [r.result for r in as_tree.body[-2].value.infer()]
        assert str(res) == "[Proxy to the object: Call: C_0(())]"
        res = [r.result.value for r in as_tree.body[-1].value.infer()]
        assert res == [0]

    def test_bool_container(self):
        """boolean operation empty container expect as False, and True otherwise"""
        as_tree, _ = self.build_tree_cfg(
            """\
                [] or {} or 1
                1 and 1 and ()
                0 or [] or (1, 2, 3)
                0 or [] or {1: "something"}
        """
        )
        res = [[r for r in b.value.infer()] for b in as_tree.body[:-2]]
        assert str(res) == "[[1], [()]]"
        res = [r for r in as_tree.body[-2].value.infer()]
        assert str(res) == "[(1, 2, 3)]"
        res = [r for r in as_tree.body[-1].value.infer()]
        assert str(res[0].result) == "{1: 'something'}"

    def test_py2_binary_op(self):
        self.setup_fcf_config(overwrite=True, py_version=2)
        as_tree, _ = self.build_tree_cfg(
            """\
                _ = 1 / 1       # int
                _ = 1.6 / 1     # float
                _ = 2 / 1.0     # float
                _ = round(x, 4)   # float
                _ = (_ * 1000) % 480
                _ = int() / 3 % 2   # int
        """,
            py2=True,
        )
        res = [[val.result_type.name for val in b.targets[0].infer()] for b in as_tree.body]
        assert res == [["int"], ["float"], ["float"], ["float"], ["float"], ["int"]]

    def test_py2_float_division(self):
        self.setup_fcf_config(overwrite=True, py_version=2)
        as_tree, _ = self.build_tree_cfg(
            """\
                s = 1.2
                z = s / 2   #@ s(value)
        """,
            py2=True,
        )
        res = [val.result.value for val in as_tree.s.infer()]
        assert res == [1.2 / 2]

    def test_binop_mixed_arith(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                def foo(x: int, y: float, z: str):
                    x + y   # float
                    y + x   # float
                    x * y   # float
                    x - y   # float
                    x + z   #@ uninf(value)
                s = "str" * 4   # str
                s = 7 * "str"
        """
        )
        res = [[val.result_type.name for val in b.value.infer()] for b in as_tree.module.body[0].body[:-1]]
        assert res == [["float"], ["float"], ["float"], ["float"]]
        res = list(as_tree.uninf.infer())
        assert str(res[0]) == "'<type(Class \"int\" in scope Module)>'"
        res = [[val.result_type.name for val in b.value.infer()] for b in as_tree.module.body[1:]]
        assert res == [["str"], ["str"]]

    def test_binop_same_operand(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                if cond():
                    x = 2
                else:
                    x = 3
                s = x + x   #@ s (value)
        """
        )
        res = [val.result.value for val in as_tree.s.infer()]
        assert res == [4, 6]

    def test_boolop_compare_multiple_same_operand(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                if cond():
                    x = 2
                else:
                    x = False
                s = x == x <= x             #@ s (value)
                bs = x and x and x or 3    #@ bs (value)
        """
        )
        res = [val.result.value for val in as_tree.s.infer()]
        assert res == [True, True]
        res = [val.result.value for val in as_tree.bs.infer()]
        assert res == [2, 3]

    def test_binop_multi_level_same_operand(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                if cond():
                    x = 2
                else:
                    x = 3
                s = x + x - x      #@ s (value) 
        """
        )
        res = [val.result.value for val in as_tree.s.infer()]
        assert res == [2, 3]

    def test_binop_same_operand_on_other_node(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                if cond():
                    x = 2
                else:
                    x = 3
                y = x * x
                s = x + y      #@ s (value) 
        """
        )
        res = [val.result.value for val in as_tree.s.infer()]
        assert res == [6, 12]

    @unittest.skip("to be implement bound conditions check to eliminate more result")
    def test_same_operand_2_different_paths(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                if cond():
                    x = 1
                    y = 10
                else:
                    x = 2
                    y = 20
                s = (x + y) + (x + y)      #@ s (value) 
        """
        )
        res = [val.result.value for val in as_tree.s.infer()]
        assert res == [6, 12]

    def test_same_operand_diff_paths(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                if cond():
                    x = 1
                else:
                    x = 2
                if cond():
                    y = 10
                else:
                    y = 20
                s = (x + y) + (x + y)      #@ s (value) 
        """
        )
        res = [val.result.value for val in as_tree.s.infer()]
        assert res == [22, 42, 24, 44]

    def test_same_operand_distant_node(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                if cond():
                    x = 1
                else:
                    x = 2
                y = x and x
                z = (y or x) + y
                s = (x + y) + z      #@ s (value) 
        """
        )
        res = [val.result.value for val in as_tree.s.infer()]
        assert res == [4, 8]

    def test_same_operand_not_infer_product(self):
        """Phi function operand is another phi function, selected_operand not updated for the nested"""
        as_tree, _ = self.build_tree_cfg(
            """\
                cm = ('cm1' if self.cm == 1 else
                      'cm4' if self.cm == 4 else
                      'cm8' if self.cm == 8 else "cmNone")
                if cm == "cm4":
                    ex = cm
                else:
                    ex = "something"
                top = ex + "some" + ex + ex + "some"  #@ s (value)
        """
        )
        res = [val.result.value for val in as_tree.s.infer()]
        assert res == [
            "cm1somecm1cm1some",
            "cm4somecm4cm4some",
            "cm8somecm8cm8some",
            "cmNonesomecmNonecmNonesome",
            "somethingsomesomethingsomethingsome",
        ]

    def test_targets_tuple(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            (a, b) = (1 + 3, 1)
            z = a
        """
        )
        result = [val.result.value for val in as_tree.body[-1].value.infer()]
        assert result == [4]

    def test_tuple_unpacking_variable(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            z = [1, 2, 5.5]
            (a, b, c) = (d, e, f) = z
            f = a + d + e + f
        """
        )
        result = [val.result.value for val in as_tree.body[-1].value.infer()]
        assert result == [9.5]

    def test_tuple_unpacking_star_var_at_the_end(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            z = [1, 2, 5.5, 7, 8]
            (a, b, c, *d) = z
            res = d[0] + d[1]
        """
        )
        result = [val.result.value for val in as_tree.body[-1].value.infer()]
        assert result == [15]

    def test_tuple_unpacking_star_var_middle(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            z = [1, 2, 5.5, 7, 8]
            (a, b, *c, d) = z
            res = c[0] + c[1]
        """
        )
        result = [val.result.value for val in as_tree.body[-1].value.infer()]
        assert result == [12.5]

    def test_nested_tuple_unpacking(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            z = [1, 2, 5.5, 7, 8]
            (a, b, *c, d), e, f = z, 1, 3
            res = c[0] + c[1] + e + f
        """
        )
        result = [val.result.value for val in as_tree.body[-1].value.infer()]
        assert result == [16.5]

    def test_phi_function(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            x = 2
            if x:
                if x:
                    y = 1
                    x = 3
                else:
                    y = 2
            else:
                y = 3
            x = y + 3 * x
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [10, 7, 11, 8, 12, 9]

    def test_looping(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                bi = 1
                b = 2
                cycle = False
                first = True
                while cycle or first:
                    b += bi
                z = b
        """
        )
        res = [r.result.value for r in as_tree.body[-1].targets[0].infer()]
        assert res == [2]

    def test_compare_node(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            y = 2 < (1 + 2) < 4
            if x:
                z = 2
            else:
                z = 10
            f = z <= 10
        """
        )
        result = [val.result.value for val in as_tree.body[0].targets[0].infer()]
        assert result == [True]
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [True, True]

    def test_ifexp_no_nested(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            x = 1 if True else 2
            y = x
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [1, 2]

    def test_ifexp_nested(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            x = 1 if True else 2 if False else 3
            y = x
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [1, 2, 3]

    def test_ifexp_unpacking(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            def foo(a):
                return a + 4
            x = 1
            x, y = (2 if xxx else foo(x)), (4 if xxx else 5)
            y = x * y
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [8, 10, 20, 25]

    def test_for_node(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            for i in z:
                y = i
                res = 2
            f = y
            f = res
            res = 4
        """
        )
        result = [val.result for val in as_tree.body[-2].targets[0].infer()]
        assert any((str(r) == "2" for r in result))

    def test_augassign(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Foo:
                x = 1
                def calc(self):
                    return self.x + 3
                def __add__(self, other):
                    other /= self.x
                    return other
            f = Foo()
            f.x += 2
            t = 1
            t *= 2
            t /= 3
            t *= f.calc()
            z = f + t   #@ s(value)
        """
        )
        result = [val.result.value for val in as_tree.s.infer()]
        assert result == [4 / 3]

    def test_cache_mechanism(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            x = 1 if cond() else 2
            z = x + x
            y = z + z
        """
        )
        res = [r.result.value for r in as_tree.body[-1].targets[0].infer(context_mod.InferenceContext())]
        assert res == [4, 8]

    def test_cache_multiple_same_result_should_not_yield(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            a = 1 if some() else 2
            a = Row(a, a)
            z = a
        """
        )
        result = [val for val in as_tree.body[-1].targets[0].infer()]
        assert len(result) == 2

    def test_builtins(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            x = 1 if cond() else 2
            a = int(x) / float(2.2 + 1.9 / 2)
            z = a
            st = str(x) + "_a_string"
            st = len(st) * st
        """
        )
        result = [val.result.value for val in as_tree.body[-3].targets[0].infer()]
        assert result == [int(1) / float(2.2 + 1.9 / 2), int(2) / float(2.2 + 1.9 / 2)]
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == ["1_a_string" * 10, "2_a_string" * 10]

    def test_repr(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            s = "something"
            repr(s)     #@ s(value)
            
            class C:
                def __init__(self, x):
                    self.x = x
                    
                def __repr__(self):
                    return repr(self.x) + "test"
            c = C(12345)
            repr(c)     #@ cl(value)
        """
        )
        result = [val.result.value for val in as_tree.s.infer()]
        assert result == ["'something'"]
        result = [val.result.value for val in as_tree.cl.infer()]
        assert result == ["12345test"]

    def test_ascii(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            s = "Pythön is interesting"
            ascii(s)     #@ s(value)
            
            class C:
                def __init__(self, x):
                    self.x = x
                    
                def __repr__(self):
                    return repr(self.x) + "test"
            c = C("Pythön is interesting")
            ascii(c)     #@ cl(value)
        """
        )
        result = [val.result.value for val in as_tree.s.infer()]
        assert result == ["'Pyth\\xf6n is interesting'"]
        result = [val.result.value for val in as_tree.cl.infer()]
        assert result == ["'Pyth\\xf6n is interesting'test"]

    def test_joined_str(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            x = "a"
            y = "b"
            s = f"{x} + {y} = {x+y} => {3} {'constant'}"
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result[0] == "a + b = ab => 3 constant"

    def test_joined_str_extra(self):
        inputs = [
            """
            name = "Fred"
            f"He said his name is {name!r}."
            """,
            """
            name = "Fred"
            f"He said his name is {repr(name)}."
            """,
            """
            width = 10
            precision = 4
            value = 12.34567
            f"result: {value:{width}.{precision}}"  # nested fields
            """,
            """
            number = 1024
            f"{number:#0x}"  # using integer format specifier
            """,
            """
            line = "The mill's closed"
            f"{line:20}"
            """,
            """
            line = "The mill's closed"
            f"{line!r:20}"
            """
        ]
        expected = [
            "He said his name is 'Fred'.",
            "He said his name is 'Fred'.",
            'result:      12.35',
            '0x400',
            "The mill's closed   ",
            '"The mill\'s closed" ',
        ]
        for inp, exp in zip(inputs, expected):
            as_tree, _ = self.build_tree_cfg(
                inp
            )
            result = [val.result.value for val in as_tree.body[-1].value.infer()]
            assert result[0] == exp

    def test_joined_str_multiple(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            x = "a" if cond() else "b"
            y = "c" if s() else "d"
            s = f"{x} + {y} = {x+y} => {3} {'constant'}"
            num = 1 if cond() else 2
            result = 12.1323 if cond() else 13.123123
            f"{result:.{num}f}"
        """
        )
        result = [val.result.value for val in as_tree.body[-4].targets[0].infer()]
        assert result == ['a + c = ac => 3 constant', 'a + d = ad => 3 constant', 'b + c = bc => 3 constant', 'b + d = bd => 3 constant']
        result = [val.result.value for val in as_tree.body[-1].value.infer()]
        assert result == ['12.1', '12.13', '13.1', '13.12']

    def test_joined_str_uninferable(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            y = "c" if s() else "d"
            s = f"{xxx} + {y} = {x+y} => {3} {'constant'}"
            s = f"{3}:.{xxx}f"
        """
        )
        result = [val.result for val in as_tree.body[-2].targets[0].infer()]
        assert type(result[0]) is nodes.Uninferable
        result = [val.result for val in as_tree.body[-1].targets[0].infer()]
        assert type(result[0]) is nodes.Uninferable


class TestContainer(BaseTestInference):
    # ------------------LIST TESTS--------------------

    def test_list_index(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            a = 4
            l = [a, 2, 3, "s"]
            s = l[3]
            var_a = l[0]
        """
        )
        result = [val.result.value for val in as_tree.body[-2].targets[0].infer()]
        assert result == ["s"]
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [4]

    def test_list_variable_index(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            a = 1 + 2 - 3
            l = [1, 2, 3, "s"]
            s = l[a + 1:a + 3]
        """
        )
        result = [val for val in as_tree.body[-1].targets[0].infer()]
        assert str(result[0].result.get_actual_container()) == "[2, 3]"

    def test_list_slicing(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            l = [1, 2, 3, "s"]
            s = l[1:]
        """
        )
        result = [val.result for val in as_tree.body[-1].targets[0].infer()]
        assert self.extract_const(result) == [[2, 3, "s"]]

    def test_uninferable_list_elem(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            l = [1, w, 3, "s"]
            s = l[1:]
        """
        )
        result = [val.result for val in as_tree.body[-1].targets[0].infer()]
        assert type(self.extract_const(result)[0]) is nodes.Uninferable

    def test_instance_in_sequence(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class C: pass
            c = C()
            l = [1, c, 3, "s"]
            s = l[1:]   #@ s(value)
        """
        )
        result = [val.result for val in as_tree.s.infer()]
        assert len(self.extract_const(result)[0]) == 3

    def test_list_phi_values(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            if True:
                li = [1, 2, 3]
                l = [1, 2, 3, "s"]
                var = 2
            else:
                li = [2, 2, 3]
                l = [4, 5, 6, True]
                var = "s"
            li_val = li[1]
            li_val = li[0]
            another_l = [var, 2, 3]
            s = l[1:]
            y = another_l[0]
        """
        )
        result = [val.result for val in as_tree.body[-2].targets[0].infer()]
        assert self.extract_const(result) == [[2, 3, "s"], [5, 6, True]]
        another_l_result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert another_l_result == [2, "s"]
        li_result = [val.result.value for val in as_tree.body[-4].targets[0].infer()]
        assert li_result == [1, 2]
        li_result = [val.result.value for val in as_tree.body[-5].targets[0].infer()]
        assert li_result == [2, 2]

    def test_list_membership(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            s = [1, 2, 3]
            if True:
                val = 1
            else:
                val = 10
            phi_res = val in s
            y = 2 in s
            z = 4 not in s
            ope = (4 not in s) & (2 not in s)   # False
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [False]
        result = [val.result.value for val in as_tree.body[-2].targets[0].infer()]
        assert result == [True]
        result = [val.result.value for val in as_tree.body[-3].targets[0].infer()]
        assert result == [True]
        result = [val.result.value for val in as_tree.body[-4].targets[0].infer()]
        assert result == [True, False]

    def test_list_mult_with_0(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            if True:
                s = 3
            else:
                s = 4
            l = [1, 2, s]
            x = 0
            z = l * x   #@ zero (value)
        """
        )
        result = [str(val.result) for val in as_tree.zero.infer()]
        assert result == ["[]"]

    def test_list_get_instance(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class C:
                x = 1
            if True:
                c = C()
            else:
                c = uninferable
            l = [1, 2, c]
            z = l[2].x   #@ s (value)
        """
        )
        result = [val.result for val in as_tree.s.infer()]
        assert result[0].value == 1

    def test_list_bin_op(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            res = []
            l = [1, 2, 3]
            s = [4, 5, 6]
            res += l       
            res += s
            z = res     #@ s (value)
        """
        )
        result = [val.result for val in as_tree.s.infer()]
        assert str(result) == "[[1, 2, 3, 4, 5, 6]]"

    @unittest.skip("drop list assignment support")
    def test_list_assignment(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            s = [1, 2, 3]
            s[0] = 7
            y = s[0] + s[1]
            s[1:] = [4, 5]
            z = s[1:]
        """
        )
        result = [val.result.value for val in as_tree.body[-3].targets[0].infer()]
        assert result == [9]
        result = [val.result for val in as_tree.body[-1].targets[0].infer()]
        assert self.extract_const(result) == [[4, 5]]

    # -------------------SET TESTS------------------------
    def test_set_const(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            s = {1, 2, 3}
            y = s
        """
        )
        result = [val.result for val in as_tree.body[-1].targets[0].infer()]
        assert self.extract_const(result) == [{1, 2, 3}]

    def test_set_bin_op(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            s = {1, 2, 3}
            d = {2, 3, 4}
            min_res = s - d
            or_res = s | d
            and_res = s & d
        """
        )
        result = [val.result for val in as_tree.body[-3].targets[0].infer()]
        assert self.extract_const(result) == [{1}]
        result = [val.result for val in as_tree.body[-2].targets[0].infer()]
        assert self.extract_const(result) == [{1, 2, 3, 4}]
        result = [val.result for val in as_tree.body[-1].targets[0].infer()]
        assert self.extract_const(result) == [{2, 3}]

    def test_set_phi_values(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            if True:
                a = 1
                ex_set = {1, 2, 3}
            else:
                a = 4
                ex_set = {10, 20, 30}
            s = {a, 2, 3}
            z = s[0]
            s = ex_set
        """
        )
        result = [val.strip_inference_result() for val in as_tree.body[-3].value.extract_const()]
        assert result == [{1, 2, 3}, {4, 2, 3}]
        result = [val.result for val in as_tree.body[-1].targets[0].infer()]
        s = self.extract_const(result)
        assert s == [{1, 2, 3}, {10, 20, 30}]

    def test_set_membership(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            s = {1, 2, 3}
            y = 2 in s  # True
            f = (3 in s) & (4 in s)   # False
        """
        )
        result = [val.result for val in as_tree.body[-2].targets[0].infer()]
        assert self.extract_const(result) == [True]
        result = [val.result for val in as_tree.body[-1].targets[0].infer()]
        assert self.extract_const(result) == [False]

    # -------------------TUPLE TESTS------------------------

    def test_tuple_simple(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            s = (1, 3, 5)
            y = s
        """
        )
        result = [val.result for val in as_tree.body[-1].targets[0].infer()]
        assert self.extract_const(result) == [(1, 3, 5)]

    def test_tuple_simple_indexing_and_slicing(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            s = (1, 3, 5)
            y = s[0] + s[2]
            sliced = s[1:]
        """
        )
        result = [val.result for val in as_tree.body[-2].targets[0].infer()]
        assert self.extract_const(result) == [6]
        result = [val.result for val in as_tree.body[-1].targets[0].infer()]
        assert self.extract_const(result) == [(3, 5)]

    def test_tuple_concatenation(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            first = (1, 3, 5)
            second = (10, 30, 50)
            y = first + second
        """
        )
        result = [val.result for val in as_tree.body[-1].targets[0].infer()]
        assert self.extract_const(result) == [(1, 3, 5, 10, 30, 50)]

    def test_tuple_repetition(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            t = (1, 3, 5)
            s = t * 3
        """
        )
        result = [val.result for val in as_tree.body[-1].targets[0].infer()]
        assert self.extract_const(result) == [(1, 3, 5, 1, 3, 5, 1, 3, 5)]

    def test_tuple_phi_values(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            if True:
                t = (1, 3, 5)
            else:
                t = (2, 3, 5)
            s = t
            s_elem = t[0]   # 1, 2
        """
        )
        result = [val.result for val in as_tree.body[-2].targets[0].infer()]
        assert self.extract_const(result) == [(1, 3, 5), (2, 3, 5)]
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [1, 2]

    def test_tuple_membership(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            t = (2, 3, 's')
            if True:
                a = 2
            else:
                a = 6
            false = a in t   # True, False
            y = 's' in t     # True
        """
        )
        result = [val.result.value for val in as_tree.body[-2].targets[0].infer()]
        assert result == [True, False]
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [True]

    def test_dictionary_with_simple_subscript(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            var = 5
            t = {'a': 2.1, 'b': 3, var: 4}
            s = t['a'] + t['b'] + t[var] + t[5]
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [13.1]

    def test_dictionary_with_value_instance(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Foo:
                x = 4
                pass
            var = 5
            t = {'a': 2.1, 'b': 3, var: Foo()}
            s = t['a'] + t['b'] + t[var].x
            s = t[var].x + s
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [13.1]


class TestInferenceInter(BaseTestInference):
    def test_simple_function_call(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            def foo(a):
                return a

            b = 4 + 3
            s = foo(b + 5)
            y = s + 4
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [16]

    def test_function_call_default_arg(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            def foo(a, b=1):
                return a + b

            b = 4 + 3
            s = foo(b + 5) + foo(1, 4)  # 13 + 5
            y = s + 4
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [22]

    def test_function_call_decorator(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            def decorator_test(f):
                def another_foo(a, b):
                    s = f(a, b)
                    return s + 1.5
                return another_foo

            @decorator_test
            def foo(a, b):
                return a + b

            @decorator_test
            def fee(c, d):
                return c * d

            y = foo(1, 2)
            z = y + fee(3, 4)
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [18.0]

    def test_function_call_chain(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            def foo(x):
                def fee(y):
                    return x + y
                return fee

            s = foo(3)(2)
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [5]

    def test_chaining_decorator(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            def add_1(f):
                def another_foo(a, b):
                    s = f(a, b)
                    return s + 1
                return another_foo

            def times_2(f):
                def another_foo(a, b):
                    s = f(a, b)
                    return s * 2
                return another_foo

            @times_2
            @add_1
            def foo(a, b):
                return a + b
            z = foo(1, 2)   # (3 + 1) * 2
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [8]

    def test_decorator_call(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            def dec(arg):
                def _wrapper(f):
                    def _w(v1, v2):
                        return f(v1, v2 + arg)
                    return _w
                return _wrapper
                
            @dec(10)
            def foo(a, b):
                return a + b
            z = foo(1, 2)   # (1  + (2 + 10))
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [13]

    def test_class_default_arg(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Foo():
                def __init__(self, a, b=1):
                    self.a = a
                    self.b = b

            f = Foo(2)
            g = Foo(4, 4)
            y = f.b + f.a + g.a + g.b
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [11]

    def test_2_function_call(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            def add(a, b):
                return a + b
            def min(a, b):
                return a - b

            a = 7 + 4
            s = add(2, 5) * min(6, (a-8) + 4 * 2)     # 7 * (6 - ((11-8) + 4 * 2))
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [-35]

    def test_nested_function_call(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            def add(a, b):
                return a + b
            def foo(a, b):
                return add(a**a, b)

            s = foo(2, 3)     # 2^2 + 3
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [7]

    def test_nested_function_call_propagating_context(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            def foo_2(a, b):
                return a - b

            def foo_1(a, b):
                return foo_2(b, a) + b  # 6

            def foo(a, b):
                s = foo_1(4, 5)   # 6
                return s + a + b

            s = foo(2, 3)     # 2^2 + 3
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [11]

    def test_different_global_call(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            def foo():
                return a + 2

            a = 1
            val_1 = foo()
            a = 2
            val_2 = val_1 + foo()   # 3 + 4
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [7]

    def test_function_call_kwargs(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            def foo(a, b=2, c=1):
                return a + b + c

            a = 1
            val_1 = foo(a)
            a = 4
            val_2 = val_1 + foo(3, c=2, b=a)
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [13]

    def test_unpack_function_return(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                def foo(a, b):
                    return a + b, b * a

                b = 4 + 3
                q, w = foo(b + 5, b)
                y = q + w
            """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [103]

    def test_unpack_class_instance(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                def foo(a, b):
                    return a + b, b * a

                b = 4 + 3
                q, w = foo(b + 5, b)
                y = q + w
            """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [103]

    def test_class_tuple_unpack(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                class Foo:
                    x = 1
                class Fee:
                    y = 3
                g, f = Foo(), Fee()
                t = g.x + f.y
            """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [4]

    # ---------------------class--------------------
    def test_class_simple_instance(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Foo:
                def __init__(self, x):
                    self.x = x
            f = Foo(1)
            y = f.x + 2
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [3]

    def test_class_definition_in_method(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Foo:
                def meth_foo(self):
                    self.x = 1
                    y = self.x
        """
        )
        result = [val.result.value for val in as_tree.body[0].body[0].body[-1].targets[0].infer()]
        assert result == [1]

    def test_class_double_instance(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            def s():
                pass
            class Foo:
                def __init__(self, x):
                    self.x = x
                    self.fee = Fee(x)
            class Fee:
                def __init__(self, y):
                    self.y = y + y
            f = Foo(2)
            s()     # updating the globals
            y = f.x + f.fee.y   # 2 + (2 + 2)
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [6]

    def test_class_unresolve_with_external_attr(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Foo:
                def __init__(self, x):
                    self.x = x
                    self.fee = Fee(x)
                    self.fee.y = 99
                    self.z = self.fee.y
                    self.z = self.z + self.fee.y
            class Fee:
                def __init__(self, y):
                    self.y = y + y
            f = Foo(2)
            y = f.x + f.fee.y   # 2 + (99)
            res = f.z
        """
        )
        result = [val.result.value for val in as_tree.body[-2].targets[0].infer()]
        assert result == [101]
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [198]

    def test_class_globals_var_constructor(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Foo:
                def __init__(self):
                    self.x = x

            x = 1
            f = Foo()
            y = f.x + 2
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [3]

    def test_class_attr_phi(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Foo:
                if True:
                    x = 1
                    y = 3
                else:
                    x = 2
                    y = 4
                def __init__(self):
                    pass

            f = Foo()
            f.y = 5
            y = f.x + f.y
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [6, 7]

    def test_class_external_attr_phi(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Foo:
                def __init__(self):
                    pass

            f = Foo()
            if True:
                f.x = 3
            else:
                f.x = 4
            y = f.x
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [3, 4]

    def test_class_external_attr_phi_(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Foo:
                def __init__(self, x=1):
                    self.x = x

                def do_x(self, y):
                    self.x = y

            f = Foo()
            f.do_x(3)
            f.do_x(7)
            y = f.x + 1
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [8]

    def test_class_insert_self(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Foo:
                def __init__(self, x=1):
                    self.x_0 = x

                def ret_self(self):
                    return self

            f = Foo()
            f_self = f.ret_self()
        """
        )
        result = [val.result for val in as_tree.body[-1].targets[0].infer()]
        assert repr(result[0]) == "Proxy to the object: Call: Foo_0(())"

    def test_class_chaining_bugs(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Foo:
                def __init__(self, x=1):
                    self.x_0 = x

                def calc(self):
                    return self.x_0

            f = Foo(2).calc()
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [2]

    def test_property(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Foo:
                @property
                def foo(self):
                    return 5

            f = Foo().foo
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [5]

    @unittest.skip("Bug: infinite recursion on second operand of phi functions when it's class instance")
    def test_class_attribute_phi_regression(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class MyClass():
                def __init__(self):
                    self.is_rebuf = self.cfg["CM"]
                    if self.is_rebuf:
                        self.cell = 5
                    else:
                        pass
            
                def top(self):
                    return self.cell
                    
            c = MyClass()
            z = c.top()
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [5]

    def test_looping_second_infinite_loop_regression(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                bi = 1
                b = 2
                cycle = False
                first = True
                while cycle or first:
                    b = bi + b
                z = b
        """
        )
        res = [r.result.value for r in as_tree.body[-1].targets[0].infer()]
        assert res == [2]


class TestDunderMethod(BaseTestInference):
    def test_add_dunder_method(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Foo:
                def __init__(self, x=1):
                    self.x = x

                def __add__(self, other):
                    return other**2

            f = Foo(99)
            x = f + 3   # 3^2
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [9]

    def test_unaryop_dunder_method(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Foo:
                def __init__(self, x=1):
                    self.x = x

                def __neg__(self):
                    return self.x + 10

            f = Foo(99)
            x = -(-f) + 3
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [-106]

    def test_dunder_method_precedence(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Foo:
                def __init__(self, x=1):
                    self.x = x

                def __add__(self, other):
                    return other**2
                
                def __radd__(self, other):
                    return self.__add__(other)

            f = Foo(99)
            x = f + 3   # 3^2
            x = 3 + f + x
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [18]

    def test_compare_dunder(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Foo:
                def __init__(self, x):
                    self.x = x
                    
                def __gt__(self, other):
                    return self.x > other

            f = Foo(4)
            t1 = f > 3 >= 3 < f     # 4 > 3 >= 3 < 4
            t2 = 5 < f > 1 < f      # 5 < 4 > 1 < 4
        """
        )
        result = [val.result.value for val in as_tree.body[-1].targets[0].infer()]
        assert result == [False]
        result = [val.result.value for val in as_tree.body[-2].targets[0].infer()]
        assert result == [True]

    def test_dunder_bool(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Foo:
                def __init__(self, x):
                    self.x = x
                    
                def __bool__(self):
                    return self.x > 3
                
                def __len__(self):
                    return 0
                    
            class Fee:
                def __init__(self, x):
                    self.x = x
                    
                def __len__(self):
                    return self.x

            f = Foo(4)
            _ = bool(f)
            fee = Fee(0)
            _ = bool(fee)
            _ = fee or f
        """
        )
        result = [val.result.value for val in as_tree.body[-4].targets[0].infer()]
        assert result == [True]
        result = [val.result.value for val in as_tree.body[-2].targets[0].infer()]
        assert result == [False]
        result = [val for val in as_tree.body[-1].targets[0].infer()]
        assert str(result[0]) == "Proxy to the object: Call: Foo_0((4,))"


class TestInterDataFlow(BaseTestInference):
    def test_global_var(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            def foo(y):
                global x
                x = 1
                x = y
                return 5
            x = 2
            foo(15)
            y = x
        """
        )
        result = list(as_tree.body[-1].targets[0].infer())
        assert result[0].result.value == 15

    def test_global_multiple_value(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            def foo(y):
                global x
                if True:
                    x = y + 1
                elif False:
                    x = y / 2
            x = 2
            foo(15)
            y = x
        """
        )
        result = [r.result.value for r in as_tree.body[-1].targets[0].infer()]
        assert result == [16, 2, 7.5]

    def test_global_branching_stmt(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            def foo(y):
                global x
                if True:
                    x = y + 1
                elif False:
                    x = y / 2
            x = 2
            if True:
                foo(15)
            else:
                x = 66
            y = x
        """
        )
        result = [r.result.value for r in as_tree.body[-1].targets[0].infer()]
        assert result == [16, 2, 7.5, 66]

    def test_global_modify_in_method(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Foo:
                def foo(self, y):
                    global x
                    if True:
                        x = y + 1
                    else:
                        x = y / 2

            f = Foo()
            f.foo(2)
            y = x
        """
        )
        result = [r.result.value for r in as_tree.body[-1].targets[0].infer()]
        assert result == [3, 1.0]

    def test_method_modifying_instance(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Foo:
                def __init__(self):
                    pass
                def foo(self, y):
                    self.x = y

            f = Foo()
            f.x = 99
            f.foo(2)
            y = f.x
        """
        )
        result = [r.result.value for r in as_tree.body[-1].targets[0].infer()]
        assert result == [2]

    def test_method_modifying_instance_repeated(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Foo:
                def __init__(self):
                    pass
                def before_foo(self, z):
                    self.z = z
                def foo(self, y):
                    self.x = y
                    self.result = self.z * self.x + self.result
            f = Foo()
            f.before_foo(3)
            f.result = 99
            f.foo(2)
            f.foo(5)
            y = f.result
        """
        )
        result = [r.result.value for r in as_tree.body[-1].targets[0].infer()]
        assert result == [120]

    def test_nested_instance_dunder(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class NestedFoo:
                def __init__(self):
                    pass
                def init(self, res):
                    self.res = res
                def __add__(self, other):
                    return other * self.res
            class Foo:
                def __init__(self):
                    pass
                def calc(self, y):
                    return self.nested_cls + y
            nf = NestedFoo()
            nf.init(5)
            f = Foo()
            f.nested_cls = nf
            s = f.calc(5)
        """
        )
        result = [r.result.value for r in as_tree.body[-1].targets[0].infer()]
        assert result == [25]

    def test_method_nested_instance(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class NestedFoo:
                def __init__(self):
                    pass
                def init(self, res):
                    self.res = res
            class Foo:
                def __init__(self):
                    pass
                def calc(self, y):
                    return self.nested_cls.res * y
            nf = NestedFoo()
            nf.init(5)
            f = Foo()
            f.nested_cls = nf
            s = f.calc(5)
        """
        )
        result = [r.result.value for r in as_tree.body[-1].targets[0].infer()]
        assert result == [25]

    def test_method_nested_instance_must_alias(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class NestedFoo:
                def __init__(self):
                    pass
                def init(self, res):
                    self.res = res
            class Foo:
                def __init__(self):
                    pass
                def calc(self, y):
                    self.nested_cls.res = 5 * y
            nf = NestedFoo()
            nf.init(5)
            f = Foo()
            f.nested_cls = nf
            f.calc(5)
            result = f.nested_cls.res
        """
        )
        result = [r.result.value for r in as_tree.body[-1].targets[0].infer()]
        assert result == [25]

    def test_method_nested_instance_must_alias_modify_nested_obj(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class NestedFoo:
                def __init__(self):
                    pass
                def init(self, res):
                    self.res = res
            class Foo:
                def __init__(self):
                    pass
                def calc(self, y):
                    self.nested_cls.res = 5 * y
            nf = NestedFoo()
            nf.init(5)
            f = Foo()
            f.nested_cls = nf
            f.calc(5)
            result = nf.res
        """
        )
        result = [r.result.value for r in as_tree.body[-1].targets[0].infer()]
        assert result == [25]

    def test_method_aliasing(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class NestedFoo:
                def __init__(self):
                    pass
                def init(self, res):
                    self.res = res
            class Foo:
                def __init__(self):
                    pass
                def calc(self, y):
                    self.nested_cls.res = 5 * y
            nf = NestedFoo()
            nf.init(5)
            f = Foo()
            f.nested_cls = nf
            calc_meth = f.calc
            calc_meth(5)
            result = nf.res
        """
        )
        result = [r.result.value for r in as_tree.body[-1].targets[0].infer()]
        assert result == [25]

    def test_global_variable_attribute_accessing(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Temp:
                x = 1
            t = Temp()

            class Foo:
                def __init__(self):
                    pass
                def calc(self):
                    self.y = t.x
                    self.y = t.x
                    return self.y

            z = Foo().calc()
        """
        )
        result = [r.result.value for r in as_tree.body[-1].targets[0].infer()]
        assert result == [1]

    def test_constructor_override_class_level_attribute(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Base:
                x = 1
                x = 5
                def __init__(self):
                    self.x = 3
            b = Base()
            z = b.x
        """
        )
        val = [val.result.value for val in as_tree.body[-1].value.infer()]
        assert val == [3]

    def test_method_modifying_other_method(self):
        """Test a method that call another method to modify the instance"""
        as_tree, _ = self.build_tree_cfg(
            """\
            class Base:
                x = 1
                x = 5
                def _fee(self):
                    self.x = 10
                def foo(self):
                    self.x = 100
                    self._fee()
            b = Base()
            b.foo()
            z = b.x
        """
        )
        val = [val.result.value for val in as_tree.body[-1].value.infer()]
        assert val == [10]


class TestInheritance(BaseTestInference):
    def test_class_attr(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Base:
                x = 1
            class Derived(Base):
                pass
            d = Derived()
            y = d.x
        """
        )
        val = [val.result.value for val in as_tree.body[-1].value.infer()]
        assert val == [1]

    def test_inherit_method(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Base:
                x = 3
                def calc_x(self):
                    return self.x * 2
            class Derived(Base):
                def __init__(self, x):
                    self.x = x
            d = Derived(30)
            y = d.calc_x()
        """
        )
        val = [val.result.value for val in as_tree.body[-1].value.infer()]
        assert val == [60]

    def test_inherit_replace_base_method(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Base:
                x = 3
                def calc_x(self):
                    return self.x * 2
            class Derived(Base):
                def __init__(self, x):
                    self.x = x
                def calc_x(self):
                    return self.x * 10
            d = Derived(30)
            y = d.calc_x()
        """
        )
        val = [val.result.value for val in as_tree.body[-1].value.infer()]
        assert val == [300]

    def test_inherit_multiple_base(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class Base1:
                x = 3
                y = 4
            class Base2:
                x = 30
                z = 40
            class Derived(Base1, Base2):
                def calc_x(self):
                    return self.x + self.y + self.z
            d = Derived()
            y = d.calc_x()
        """
        )
        val = [val.result.value for val in as_tree.body[-1].value.infer()]
        assert val == [47]

    def test_multiple_inheritance(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class A:
                def calc_x(self):
                    return 10
            class B(A):
                def calc_x(self):
                    return 20
            class C(B):
                pass
            c_cls = C()
            y = c_cls.calc_x()
        """
        )
        val = [val.result.value for val in as_tree.body[-1].value.infer()]
        assert val == [20]

    def test_diamond(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class A:
                def process(self):
                    return 10
            class B(A):
                pass
            class C(A):
                def process(self):
                    return 20
            class D(B,C): pass
            obj = D()
            obj.process()
        """
        )
        val = [val.result.value for val in as_tree.body[-1].value.infer()]
        assert val == [20]

    def test_inconsistent_mro(self):
        with self.assertRaises(exceptions.InconsistentMroError):
            as_tree, _ = self.build_tree_cfg(
                """\
                class A:
                    def process(self):
                        return 30
                class B(A):
                    def process(self):
                        return 40
                class C(A, B):
                    pass
                obj = C()
                obj.process()
            """
            )
            list(as_tree.body[-1].value.infer())

    def test_duplicate_base(self):
        with self.assertRaises(exceptions.DuplicateBasesError):
            as_tree, _ = self.build_tree_cfg(
                """\
                class A:
                    def process(self):
                        return 30
                class C(A, A):
                    pass
                obj = C()
                obj.process()
            """
            )
            list(as_tree.body[-1].value.infer())


class TestAliasing(BaseTestInference):
    def test_global_var(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            class F:
                def __init__(self):
                    self.x = 1
            f = F()
            g = f
            z = g.x
        """
        )
        ins = as_tree.body[-1].value.instance()
        # assert instance is the ClassInstance get from the F() call
        assert ins == as_tree.instance_dict[as_tree.body[1].value]


class TestErrorHandling(BaseTestInference):
    def test_unimplemented_dunder(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                class Foo:
                    def __init__(self, x):
                        self.x = x
                    def __ge__(self, other):
                        return 1.5
                f = Foo()
                result = (f > 1) == 2
        """
        )
        result = [r.status for r in as_tree.body[-1].targets[0].infer()]
        assert result == [False]

    def test_infer_unknown_value(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                def foo(a: int, b: float, c):
                    z = a + b + c

        """
        )
        res = [r.result for r in as_tree.body[0].body[0].targets[0].infer()]
        assert isinstance(res[0], nodes.Uninferable)

    def test_invalid_name(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                a = x
                t = a
        """
        )
        res = [r.result for r in as_tree.body[-1].targets[0].infer()]
        assert isinstance(res[0], nodes.Uninferable)

    def test_unknown_unaryop(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                z = -a
        """
        )
        res = [r.result for r in as_tree.body[0].targets[0].infer()]
        assert isinstance(res[0], nodes.Uninferable)

    def test_none_binary_op(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                class C(Com):
                    def foo(self):
                        if Cond():
                            x = self.some
                        else:
                            x = None
                        z = x % 8
                        y = x < 1
        """
        )
        res = [r.result for r in as_tree.body[0].body[0].body[-2].targets[0].infer()]
        assert isinstance(res[0], nodes.Uninferable)
        res = list(as_tree.body[0].body[0].body[-1].targets[0].infer())
        # test one of that has bool type inference
        assert any((r.result_type.name == "bool" for r in res))

    def test_dict_list_method(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                ta = bin(x)
                ta = ta[2:]
                msb = (number-1) - ta.find(1)
                d = {1: 2, 3: 5}
                d.update({4: 6, 7: 8})
                {1, 2, 3}.add({3, 4, 5})
                (1, 2, 3).index(2)
        """
        )
        res = [r.result for r in as_tree.body[1].targets[0].infer()]
        assert isinstance(res[0], nodes.Uninferable)

    def test_invalid_attr(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                "something".index(2)
                (1 + 2).something()
        """
        )
        results = [r.result for b in as_tree.body for r in b.infer()]
        for r in results:
            assert isinstance(r, nodes.Uninferable)

    def test_list_class_instance(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                lcen = 2
                lcen_it = 3
                num = 0
                num2 = 2
                s = [lcen] * (1 - num) + [lcen_it] * num2   #@ s(value)
        """
        )
        res = [r.result for r in as_tree.s.infer()]
        assert len(res[0].elts) == 3


class TestImpossiblInference(BaseTestInference):
    def test_importing_library(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                from c.t import ca
                class Foo:
                    def __init__(self, x):
                        self.x = x
                    def foo(self):
                        self.asd = ca.ProgPoint()
                        self.another = ca.ProgPoint()
                        return self.another
                f = Foo()
                z = f.foo()
        """
        )
        res = [r.result for r in as_tree.body[-1].targets[0].infer()]
        assert res[0].msg == "can't resolve call to ca.ProgPoint"

    def test_unknown_instance(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                class Foo(ca.compiler):
                    def __init__(self, x):
                        self.x = x
                    def foo(self):
                        self.another = self.cfg['some']
        """
        )
        res = [r.result for r in as_tree.body[0].body[1].body[-1].targets[0].infer()]
        assert res[0].msg.strip() == "Inference failed for node: self.cfg['some']"

    def test_unknown_arg(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                def foo(self, sac):
                    z = sac == 1
        """
        )
        res = [r for r in as_tree.body[0].body[0].targets[0].infer()]
        assert res[0].status is False

    def test_infer_container_invalid_bin_op(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                count = 0 if True else 1
                z = [1] * None
                z[count] += 3
        """
        )
        res = [r.result for r in as_tree.body[-1].infer()]
        assert isinstance(res[0], nodes.Uninferable)

    def test_import_accessing(self):
        as_tree, _ = self.build_tree_cfg(
            """\
                import sys
                sys.path.append()
                x = 1
        """
        )
        res = [r.result for r in as_tree.body[-1].infer()]
        assert isinstance(res[0], nodes.Uninferable)

    def test_name_in_comprehension(self):
        as_tree, _ = self.build_tree_cfg(
            """\
            term = 1
            if not any((term in cachedir) for term in ('cache', 'tmp')):
                pass
            z = term
        """
        )
        res = [r.result.value for r in as_tree.body[-1].targets[0].infer()]
        assert res == [1]

    def test_slice_unaryop_regression(self):
        as_tree, _ = self.build_tree_cfg("x[-1:-1:-1]")
        assert str(as_tree.body[0]) == "x[-(1):-(1):-(1)]"

    def test_kwarg_on_func(self):
        """Test kwarg on func that didn't contain that arg"""
        as_tree, _ = self.build_tree_cfg(
            """\
            def func(j):
                return 4
            s = func(kw=3)
        """
        )
        res = [r.result.value for r in as_tree.body[-1].targets[0].infer()]
        assert res == [4]

    def test_lambda(self):
        """Test lambda call"""
        as_tree, _ = self.build_tree_cfg(
            """\
            def func(x, y):
                return x(y)
            s = func(lambda z: z + z + z * z, 2)
        """
        )
        res = [r.result.value for r in as_tree.body[-1].targets[0].infer()]
        assert res == [8]

    def test_lambda_nested(self):
        """Test lambda call"""
        as_tree, _ = self.build_tree_cfg(
            """\
            def func(x):
                return x(2)(2)
            s = func(lambda outer: lambda inner: outer * inner)
        """
        )
        res = [r.result.value for r in as_tree.body[-1].targets[0].infer()]
        assert res == [4]
