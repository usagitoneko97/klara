Customize Coverage Strategy
---------------------------

In some instance, we'll want to customize the coverage strategy to only consider few fields/parameters
for test coverage, especially when the test case generated is huge, and some parameters to a call, or any field
to any node is not necessary to include in the coverage analysis. For example, consider following::

    def foo(a: int, b: int):
        val1 = 3 if a > 0 else 4
        val2 = 5 if b > 0 else 6
        return Component(val1, val2)

If we run this with ``Klara``, it will generate following test case::

    import source


    def test_foo_0():
        assert source.foo(1, 1) is not None
        assert source.foo(1, 0) is not None
        assert source.foo(0, 1) is not None
        assert source.foo(0, 0) is not None

We've determine that the second argument to the class `Component` is unnecessary in test case generation, to
tell klara that, we'll need to define some inference extension, just like in `extending user type <extending_user_type.html>`_

First, we'll define `InferProxy` to wrap `Component()` call. ::

    class Component:
        def __init__(self, val1: int, val2=None):
            self.val1 = val1
            self.val2 = val2

    class ComponentProxy(klara.InferProxy):
        def __init__(self, value: Component):
            super(ComponentProxy, self).__init__(value)

Next, we'll define predicate of `Component()` call, which is just check the string of the call::

    def _is_component_call(node: klara.Call):
        return str(node.func) == "Component"

Next, we'll define the inference function for the `Component` call. We'll only infer for the first argument,
since we've establish that the second argument is unnecessary for test coverage.::

    @klara.inference.inference_transform_wrapper
    def _infer_call(node: klara.Call, context):
        first_arg = node.args[0]
        for first_val_result in first_arg.infer(context):
            first_val = first_val_result.strip_inference_result()
            component = Component(first_val)
            yield klara.inference.InferenceResult.load_result(ComponentProxy(component),
                                                              inference_results=(first_val,))

.. note::
    the ``inference_results`` attribute to ``load_result`` is important, in order to include the constraints,
    and some other metadata that associate with the result. If we omit that, klara wouldn't pick up the constraints,
    and won't be able to generate correct inputs.

Putting all together, with `register()` function to register our inference extension::

    # content of component_extension.py
    import klara
    import ast


    class Component:
        def __init__(self, val1: int, val2=None):
            self.val1 = val1
            self.val2 = val2


    class ComponentProxy(klara.InferProxy):
        def __init__(self, value: Component):
            super(ComponentProxy, self).__init__(value)


    @klara.inference.inference_transform_wrapper
    def _infer_call(node: klara.Call, context):
        first_arg = node.args[0]
        for first_val_result in first_arg.infer(context):
            first_val = first_val_result.strip_inference_result()
            component = Component(first_val)
            yield klara.inference.InferenceResult.load_result(ComponentProxy(component),
                                                              inference_results=(first_val,))


    def _is_component_call(node: klara.Call):
        return str(node.func) == "Component"


    def register():
        klara.MANAGER.register_transform(klara.Call, _infer_call)


We'll run the source file with klara, and provide the file above as ``--infer-extension``, something like::

    klara source.py --infer-extension component_extension.py

It will generate ``test_source.py``::

    import source


    def test_foo_0():
        assert source.foo(1, 0) == <<run_path>.Component object at 0x7f67ec2560a0>
        assert source.foo(0, 0) == <<run_path>.Component object at 0x7f67ec3d9f10>

Since we've custom defined component, we'll need to define `to_ast` method to `ComponentProxy`, to tell Klara
how to generate ast statements from that class::

    class ComponentProxy(klara.InferProxy):
        def __init__(self, value: Component):
            super(ComponentProxy, self).__init__(value)

        def to_ast(self):
            return ast.Call(func=ast.Name(id="Component", ctx=ast.Load()),
                            args=[ast.Constant(value=self.value.val1)],
                            keywords=[])

This will generate::

    import source


    def test_foo_0():
        assert source.foo(1, 0) == Component(3)
        assert source.foo(0, 0) == Component(4)

This example is in `klara/examples/cover_select_field/`