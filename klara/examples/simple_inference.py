import klara

if __name__ == "__main__":
    source = """

    def foo(func):
        x = 1
        y = 10
        y = 20
        s = (x + y) + (x + y)
        return func(s)

    s = foo(lambda x: x * x)  #@ assign(value)
    """
    tree = klara.parse(source)
    print(list(tree.body[-1].value.infer()))
    # [1764]

    # using `#@` notation to refer to node
    tree = klara.parse_node(source).assign
    print(list(tree.infer()))
    # [1764]
