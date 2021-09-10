Extending Klara
===============
.. note::
    The interface is shamelessly stolen from the `Astroid <https://github.com/PyCQA/astroid>`_ project

Klara might not covered all features that you need, or there are custom behaviour interaction with
user defined type that you wish can be included in inference system. This is where Klara's plugin interface
came into picture.

Node transformation
-------------------
Before we introduce inference extension, we'll need to introduce node transformation. Node transformation
allows Klara to transform a node during ast parsing.

The transform function need to be registered with the manager, i.e. `klara.MANAGER`. You'll need:
1. The type of the node
2. The transform function that return a new node
3. A predicate function that receives node as argument and return a boolean to specify if transform should be happening.

Let's assume that we'll want to transform all ``a // b`` operation to a function call ``floor(a, b)``.

We'll write the following function that will return a new `Call` node from a `BinOp` argument. We'll need to construct
a new node ``klara.Call``. The node is similar to python's ast, and you can refer to `python nodes documentation <https://greentreesnakes.readthedocs.io/en/latest/nodes.html>`_
for more information. In Klara, we also maintain parent/child attribute between nodes, so you'll need to
specify parent at the constructor, and specify node's other attribute in ``postinit()``.::

    import klara

    def transform_floor_call(node: klara.BinOp) -> klara.Call:
        call_node = klara.Call(parent=node.parent)
        name = klara.Name(parent=call_node)
        name.postinit(id="floor")
        args = [node.left, node.right]
        call_node.postinit(name, args, [])
        return call_node


Then, we'll create a predicate function that only target "//" operaton::

    def is_floor_op(node: klara.BinOp):
        return node.op == "//"


Finally, we'll register the transform via `MANAGER`.::

    klara.MANAGER.register_transform(klara.BinOp, transform_floor_call, is_floor_op)

We can verify the transformation by parsing a source::

    source = """
        z = a // b
    """
    tree = klara.parse(source)
    print(tree.body[0].value)

This will print a function call `floor((a, b))`.

Putting all together::

    import klara

    def transform_floor_call(node: klara.BinOp) -> klara.Call:
        call_node = klara.Call(parent=node.parent)
        name = klara.Name(parent=call_node)
        name.postinit(id="floor")
        args = [node.left, node.right]
        call_node.postinit(name, args, [])
        return call_node


    def is_floor_op(node: klara.BinOp):
        return node.op == "//"


    klara.MANAGER.register_transform(klara.BinOp, transform_floor_call, is_floor_op)

    source = """
        z = a // b
    """
    tree = klara.parse(source)
    print(tree.body[0].value)


Extending Inference
-------------------
Extending node inference is similar to extending a node. Say we'll want to implement `abs()` builtin function.

.. note::
    some of the builtin functions (abs, int, float, str, len, round) has been implemented in
    `klara/plugins/builtin_inference.py` file.

we'll first start with the infer function for the `abs()` call::

    @klara.inference.inference_transform_wrapper
    def infer_abs(node: klara.Call, context=None):
        arg = node.args[0]
        for value in arg.infer(context):
            if value.status and isinstance(value.result, klara.Const):
                yield klara.inference.InferenceResult.load_result(abs(value.result.value))
            else:
                raise klara.inference.UseInferenceDefault()

First, it will `infer()` the value of the first argument, and only apply `abs()` to a constant. We'll
also need to return an InferenceResult type. Finally, we'll raise `klara.inference.UseInferenceDefault()`
to use the default inference.

Next, we'll write the predicate, which is just checking the function name as "abs".::

    def is_abs_call(node: klara.Call):
        return str(node.func) == "abs"

Finally, we'll register everything together.::

    klara.MANAGER.register_transform(klara.Call, infer_abs, is_abs_call)

We can test it out by parsing a source, and infer the corresponding node.::

    source = """
    s = 1 - 3
    s *= 3
    z = abs(s)
    """
    tree = klara.parse(source)
    print(list(tree.body[-1].value.infer()))

Which will print out `[6]`

Putting everything together::

    import klara

    @klara.inference.inference_transform_wrapper
    def infer_abs(node: klara.Call, context=None):
        arg = node.args[0]
        for value in arg.infer(context):
            if value.status and isinstance(value.result, klara.Const):
                yield klara.inference.InferenceResult.load_result(abs(value.result.value))
            else:
                raise klara.inference.UseInferenceDefault()

    def is_abs_call(node: klara.Call):
        return str(node.func) == "abs"

    klara.MANAGER.register_transform(klara.Call, infer_abs, is_abs_call)

    source = """
    s = 1 - 3
    s *= 3
    z = abs(s)
    """
    tree = klara.parse(source)
    print(list(tree.body[-1].value.infer()))
    # [3]

Inserting as a plugin
---------------------
We can also put the transform in a file, and load it as a plugin via ``--infer-extension`` flag to `klara` command.
We can then place the code above in a file, and additionally create a function called `register()` and
`unregister()` that contain code to register/unregister inference transform::

    import klara


    @klara.inference.inference_transform_wrapper
    def infer_abs(node: klara.Call, context=None):
        arg = node.args[0]
        for value in arg.infer(context):
            if value.status and isinstance(value.result, klara.Const):
                yield klara.inference.InferenceResult.load_result(abs(value.result.value))
            else:
                raise klara.inference.UseInferenceDefault()


    def is_abs_call(node: klara.Call):
        return str(node.func) == "abs"


    def register():
        klara.MANAGER.register_transform(klara.Call, infer_abs, is_abs_call)

    def unregister():
        klara.MANAGER.unregister_transform(klara.Call, infer_abs, is_abs_call)

We can then run with klara, with following python file ``source.py``::

    def foo(v1: int, v2: int):
        if v1 > v2:
            return v1 + abs(-999)
        else:
            return -v2

And assuming that the inference transform file is called ``inference_extension.py``, we can then invoke klara by::

    klara source.py --infer-extension inference_extension.py

which will generate `test_source.py`::

    import source


    def test_foo_0():
        assert source.foo(0, -1) == 999
        assert source.foo(0, 0) == 0

Klara contain some plugins for python's built in function, typeshed etc... that can be found in `klara/plugins/` and
`klara/klara_z3/plugins` directory.
