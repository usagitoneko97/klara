from pkgutil import simplegeneric


@simplegeneric
def foo(arg):
    print(arg)
    pass


@foo.register(int)
def _(arg):
    print("integer: {}".format(arg))


@foo.register(str)
def _(arg):
    print("string : {}".format(arg))


def main():
    foo(1.234)


if __name__ == '__main__':
    main()
