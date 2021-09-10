How Does It Work?
=================

This is a gentle introduction to Klara's internal

Test case generation
--------------------
The majority of Klara is built on the inference system. Consider the function below::

    def foo(v1: int, v2: int):
        if v1 > v2:
            return 1
        else:
            return 10

If we try to infer the return value, we'll get::

    [InferenceResult(value=1, z3_assumptions=[v1 > v2]),
     InferenceResult(value=10, z3_assumptions=[Not(v1 > v2])]

From the InferenceResult, we'll obtain the `z3 assumptions` that are sets of constraints that need to be
True to get the corresponding value.

We'll then consult the Z3 to generate a model that satisfy the constraint. The process can be simplified as::

    >>> import z3
    >>> v1 = z3.Int("v1")
    >>> v2 = z3.Int("v2")
    >>> solver = z3.Solver()
    >>> solver.add(v1 > v2)
    >>> if solver.check() == z3.sat:
    ...     model = solver.model()
    ...     print(model)
    [v1 = 1, v2 = 0]

And for the value 10.::

    >>> solver.reset()
    >>> solver.add(z3.Not(v1 > v2))
    >>> if solver.check() == z3.sat:
    ...     model = solver.model()
    ...     print(model)
    [v1 = 0, v2 = 0]

Now, we have 2 sets of arguments, ``[v1 = 1, v2 = 0]`` and ``[v1 = 0, v2 = 0]`` and we can generate 2 function
call that cover all return values from the function.

Z3 solver Integration
---------------------

Let's look closer at the interaction between inference system and Z3. For code below, say we want to ``infer()``
The value of variable ``target``, assume that we have already setup function `foo`'s arguments as z3 variable ::

    def foo(v1: int):
        target = v1 + 3

If we ``infer()`` target, it will return ``infer_binop`` with ``v1 + 3``. Since we have setup `v1` as Z3 variable,
``infer()`` of `v1` will return a special value that emulates Z3 variable, and when it involve with other operation (e.g.
v1 + 3), it will return InferenceResult of Z3 binop `v1 + 3`.

In a slightly complex example below::

    def foo(v1: int, v2: int):
        if v1 > v2:
            return 1 + v2 + v1
        else:
            return 10 - v1

We'll obtain Inference result of both result and z3 assumptions in a form of z3 expression. We'll solve for
z3 assumptions as usual and obtain the model, which we'll substitute in the result to give us a constant
that can be tested in pytest. The test file will generated for input above::

    import test


    def test_foo_0():
        assert test.foo(0, -1) == 0
        assert test.foo(0, 0) == 10


