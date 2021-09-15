Limitation
==========

Python Syntax
-------------

**Loop** in general is not supported due to complex data flow analysis needed. It could be supported in the future
after I have some sort of idea how people are doing it. Loop includes ``For``, ``While`` and  ``recursive call``

**Import** is not supported yet, though it's likely to be supported in the future since it's not that difficult.

All comprehensions are not supported.

Python data structure (list, set, tuple, dict) is supported in inference system, but it's not supported
when it's used as a constraint, e.g. checking ``len()`` or testing membership.

**Exceptions** is not supported now and will simply get ignored. In the future, Klara will be able to generate
inputs to trigger exceptions, with contract support.

Uninferable
-----------

If the return value doesn't understand by Klara (e.g. multiply a list with z3 variable, which is possible
in python context, but invalid in Z3 context), it will yield a special node called uninferable. Even though
the value can't be determined, but it will still contain bound conditions. Consider following::

    def foo(v1: int):
        return 3 if v1 > 2 else xxx

The function can return the number 3, or the invalid variable ``xxx``. Even though we can't determine
the value of ``xxx``, it will still contain the bound: ``not(v1 > 2)``, so Klara still be able to generate
2 test cases for this function, using ``is not None`` as test.::

    def test_foo_0():
        assert foo(3) == 3
        assert foo(0) is not None


There will be a lot of undocumented cases of uninferable that doesn't contain the expected bound. One example
is where binary operation with list, the bound for the element of the list will not include in the uninferable
result. E.g.::

    def foo(v1: int, v2: int):
        a = 1 if v1 > 3 else 2
        b = 3 if v2 > 3 else 4
        return [a, b] * xxx

Because ``[a, b] * v1`` will be uninferable since `xxx` is undefined, this test case
will not yield any test inputs, even though the list: ``[a, b]`` will have 4 combinations in total. This
is because the ``xxx`` of binop: ``[a, b] * xxx`` is uninferable, the left hand side operand will not
get expanded.


