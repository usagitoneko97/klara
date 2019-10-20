a = 2
-a
x = 1 + 2
def decoratorEx(someFunc):
    """
    this is a decorator example
    """

    def wrapper():
        def someFunc():
            pass
        pass

    return wrapper

@decoratorEx
def foo():
    pass