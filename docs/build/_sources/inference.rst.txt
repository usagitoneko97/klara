Inference
=========
Inference provides a way to statically interpret python code, and it's in the core of automatic test case
generation.

Every ast node has corresponding ``infer()`` method, that returns a generator for potentially multiple values.
Just a simple example to illustrate::

    if x:
        s = 1
    else:
        s = 2
    d = 3 if y else 4
    z = s + d

The variable `s` can take the value of `1` or `2`, and vice versa for variable `d`. The binary operation between
`s` and `d` will produce 4 values, which is product of both operands.
To find that out in klara, we can utilize the `infer()` call on the node, assuming that `source`
variable contain the program above.::

    >>> import klara
    >>> tree = klara.parse(source)
    >>> expr = tree.body[-1].value
    >>> print(expr)
    s + d
    >>> result = list(expr.infer())
    >>> print(result)
    [4, 5, 5, 6]

In some cases Klara can't infer some node due to limited understanding or value is undefined in python,
it will yield `klara.Uninferable()` node and no exception will be thrown. For following example, there is
one path where its value is undefined, Klara will still able to infer all other possible values.::

    if x > 1:
        s = undefined
    elif x < 1:
        s = "str"
    else:
        s = 2
    z = s + 3

Running the example above, Klara will produce::

    [Uninferable, 5]

By design, Klara tried to eliminate false-positive value that is, the control path corresponding
to the value is invalid. One example is::

    v1 = "a" if cond1() else "b"
    z = v1 + v1 + v1

Each `v1` has 2 possible values. But since the binary operation `v1 + v1` refer to the same variable,
ultimately it only produce 2 values, which is ``['aaa', bbb']``.

Since Klara has z3-solver support in the inference system, it can also be used to check path feasibility
for more accuracy. For example::

    def foo(v1: int):
        if v1 > 4:
            if v1 < 3:
                z = 1
            else:
                z = 2
        else:
            z = 3
        s = z

The statement ``z = 1`` at line 4 is unreachable since the constraints: `v1 > 4` and `v1 < 3` is unsat. To
do it in Klara, we need a way to tell Klara that the argument `v1` should be converted to z3 int variable
for symbolic interpretation. We can use ``MANAGER.initialize_z3_var_from_func(func)`` to register all arguments
that are annotated in the `func` to be z3 symbols.::

    >>> import klara
    >>> tree = klara.parse(source)
    >>> with klara.MANAGER.initialize_z3_var_from_func(tree.body[0]):
    ...     print(list(tree.body[0].body[-1].value.infer()))
    [2, 3]

The value `1` is not printed since the constraints is unsat.

.. note::
    if it's inferring without registering the argument as z3 symbol, no constraint checking will
    take place, the variable `s` will inferred as ``[1, 2, 3]``

Inference Result
----------------
All `infer()` returned result will wrapped in a class called `Klara.inference.InferenceResult`, that
provide some helpful attributes.

- InferenceResult.status is a boolean. True if value is successfully inferred, false if otherwise.
- InferenceResult.result is the inferred value. This is also a `Klara.BaseNode`, since you can yield value other than const.
- InferenceResult.z3_assumptions is a set containing the constraints related to this value.
- InferenceResult.type is the type of the value. It's also can be used as type inference (e.g. inferring function argument).

Supported features
------------------

This section will give reader a view on what sort of features that Klara support. Checking the test case
`(test/test_core/test_inference.py)` here is also a good idea to understand features implemented.

Container/data structure
~~~~~~~~~~~~~~~~~~~~~~~~
Basic features on python data structure (list, set, tuple, dict) is implemented, without dynamic
modification support.

