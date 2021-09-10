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


if __name__ == "__main__":
    klara.MANAGER.register_transform(klara.BinOp, transform_floor_call, is_floor_op)

    source = """
            z = a // b
        """
    tree = klara.parse(source)
    print(tree.body[0].value)
