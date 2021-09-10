.. _extending_user_type:

Extending Inference with User defined type
==========================================

With the available interface to extend the inference, described at `previous <extending.html>`_ section, Klara also provide
wrapper to defined any user type, and how should the user type evolve over any python operation. This is
how we extend the inference to support `z3`.

At sections below, we'll look at how we integrate z3 step by step, and by the end of the sections, you
should have a good understandings on how to introduce any new user type.

Defining the wrapper
--------------------
First, we'll define the data type class, which will subclass from `klara.InferProxy`.::

    import klara

    class Z3Proxy(klara.InferProxy):
        def __init__(self, z3_expr):
            super(Z3Proxy, self).__init__(z3_expr)

`klara.InferProxy` itself is subclass of ``klara.Const`` node, which the ``value`` attribute will
hold our datatype, in this case, a Z3 expression. With this, we've defined our type and ready to
use it.

Define inferring point
----------------------

Next, we'll need to tell the inference system which node will inferred to our data type. We can use
the method described in `extending <extending.html>`_ to register plugins to customize the system
in order to yield ``Z3Proxy`` on certain node. In this case, we'll want to convert an argument
with type annotation to z3 expression. I.e.::

    def foo(a: int, b: str):
        return 1 if a > 2 and b == "s" else 2

We'll want to convert python ``klara.Compare`` node: ``a > 2`` to a z3 expression equivalent, the comparison
will convert to something like below::

    >>> a = z3.Int("a")
    >>> b = z3.String("b")
    >>> expr = z3.And(a > 2, b == z3.StringVal("s"))
    >>> Z3Proxy(expr)
    And(a > 2, b == "s")

We then need to define our custom infer function for `klara.Arg`.::

    import builtins

    AST2Z3TYPE_MAP = {"int": z3.Int, "float": z3.Real, "bool": z3.Bool, "str": z3.String}

    @klara.inference.inference_transform_wrapper
    def _infer_arg(node: klara.Arg, context):
        name = node.arg
        z3_var_type = AST2Z3TYPE_MAP[node.annotation]
        z3_var = z3_var_type(name)
        proxy = Z3Proxy(z3_var)
        yield klara.inference.InferenceResult.load_result(proxy)

    klara.MANAGER.register_transform(nodes.Arg, _infer_arg)

.. note::
    This is a very minimal implementation, and it does not handle errors. (e.g. when annotation is another type).
    In case there is error, the function can raise ``klara.inference.UseInferenceDefault`` to proceed with default
    or other plugins.

Define python operation
-----------------------

With above, we should be able to yield the z3 expression on any annotated function argument. So far, we've
only covered z3 variable construction. We'll also need to specify how this variable go through binary operation,
compare, etc... (e.g. to build ``a + 2 > 12`` z3 expression). We can do it easily by using special dunder
method, but with ``__k_`` prefix. This is to avoid clashing with the actual dunder method.::

    class Z3Proxy(klara.InferProxy):
        def __init__(self, z3_expr=None):
            super(Z3Proxy, self).__init__(z3_expr)

        def __k_add__(self, other: klara.Const):
            """represent __add__ dunder method"""
            left = self.value
            right = other.value
            expr = left + right
            # we'll create a new Z3Proxy, wrapping the new expression
            return klara.inference.InferenceResult.load_result(Z3Proxy(expr))

        def __k_eq__(self, other: klara.Const):
            left = self.value
            right = other.value
            expr = left == right
            return klara.inference.InferenceResult.load_result(Z3Proxy(expr))

        def __k_bool__(self):
            yield klara.inference.InferenceResult(self, status=True)

.. note::
    the reason why ``__k_bool__`` is needed because in Compare node, Python will call bool() on the value to
    determine if the result is true or false. `source <https://docs.python.org/3/reference/datamodel.html#object.__ge__>`_

Using it
--------

We should be able to obtain any expression with only `+` and `==` operation. We can then use the inferred
value, for example, query the z3 solver::

    source = """
        def foo(a: int):
            return a + 2 == 12
        """
    tree = klara.parse(source)
    for res in tree.body[0].infer_return_value():
        z3.solve(res.result.value)

Putting it all together

.. include:: ../../klara/examples/infer_z3.py
    :code: python

Which will print::
    [a = 10]
