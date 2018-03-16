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


print("hello world")