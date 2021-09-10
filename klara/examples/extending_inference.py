import klara


@klara.inference.inference_transform_wrapper
def infer_abs(node: klara.Call, context=None):
    arg = node.args[0]
    for value in arg.infer(context):
        if value.status and isinstance(value.result, klara.Const):
            yield from klara.inference.const_factory(abs(value.result.value))
        else:
            raise klara.inference.UseInferenceDefault()


def is_abs_call(node: klara.Call):
    return str(node.func) == "abs"


def register():
    klara.MANAGER.register_transform(klara.Call, infer_abs, is_abs_call)


if __name__ == "__main__":
    klara.MANAGER.register_transform(klara.Call, infer_abs, is_abs_call)

    source = """
    s = 1 - 2
    s *= 3
    z = abs(s)
    """
    tree = klara.parse(source)
    print(list(tree.body[-1].value.infer()))
    # [3]
