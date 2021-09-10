import klara
import ast


class Component:
    def __init__(self, val1: int, val2=None):
        self.val1 = val1
        self.val2 = val2


class ComponentProxy(klara.InferProxy):
    def __init__(self, value: Component):
        super(ComponentProxy, self).__init__(value)

    def to_ast(self):
        return ast.Call(func=ast.Name(id="Component", ctx=ast.Load()),
                        args=[ast.Constant(value=self.value.val1)],
                        keywords=[])


@klara.inference.inference_transform_wrapper
def _infer_call(node: klara.Call, context):
    first_arg = node.args[0]
    for first_val_result in first_arg.infer(context):
        first_val = first_val_result.strip_inference_result()
        component = Component(first_val)
        yield klara.inference.InferenceResult.load_result(ComponentProxy(component),
                                                          inference_results=(first_val_result,))


def _is_component_call(node: klara.Call):
    return str(node.func) == "Component"


def register():
    klara.MANAGER.register_transform(klara.Call, _infer_call)
