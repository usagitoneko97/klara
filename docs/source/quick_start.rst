Quick Start
===========

The quickest way to start is to run klara on a python file containing python function that is annotated with type
hints. E.g. we have a file called ``foo.py``::

    def foo(x: int, y: int, z: str):
        if x + y > 2:
            return x + y + 12
        elif x < y:
            return x + y
        elif (z + "me") == "some":
            return z + "thing"
        else:
            return x - y

We can invoke klara on that file by::

    klara foo.py

And it will generate a test file ``test_foo.py`` in the same directory, filled with the various test inputs::

    import contract_test


    def test_foo_0():
        assert contract_test.foo(0, 3, \'\') == 15
        assert contract_test.foo(0, 1, \'\') == 1
        assert contract_test.foo(0, 0, \'so\') == \'sothing\'
        assert contract_test.foo(0, 0, \'\') == 0

In order to fine tune test inputs generation, Klara integrates well with `icontract <https://github.com/Parquery/icontract>`_.
It will statically read the icontract decorator::


.. code-block:: python
    :linenos:

    import icontract

    @icontract.require(lambda x: x > 100)
    @icontract.ensure(lambda result: result > 200)
    def foo(x: int, y: int, z: str):
        if x + y > 2:
            return x + y + 12
        elif x < y:
            return x + y
        elif (z + "me") == "some":
            return z + "thing"
        else:
            return x - y


Which will require that `x` argument is more than 100, and that the returned result is more than 200. Note that `return z + "thing"`
at line 11 is returning a string, thus the constraint `result > 200` is invalid. Klara is fault tolerant by design,
thus any constraint that is invalid will be skipped with warnings. This will result in the following test case::

    import foo


    def test_foo_0():
        assert foo.foo(101, 88, '') == 201
        assert foo.foo(101, -99, 'so') == 'sothing'
        assert foo.foo(101, -100, '') == 201


