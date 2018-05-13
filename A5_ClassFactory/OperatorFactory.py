import ast

context = {}

class Operator(object):
    def execute(self):
        raise Exception('execute method is not defined!')

def OperatorFactory(name, argnames, exec_func, repr_func, BaseClass=Operator):
    def __constructor__(self, **kwargs):
        for key, value in kwargs.items():
            if key not in argnames:
                raise TypeError('Argument %s not valid for %s' % (key, self.__class__.__name__))
            setattr(self, key, value)

    new_class = type(name, (BaseClass,), {"__init__": __constructor__,
                                          "execute": exec_func,
                                          "__repr__": repr_func
                                          })
    return new_class

def add(self):
    return self.left + self.right

def add_repr(self):
    return str(self.left) + ' + ' + str(self.right)

BinaryAddTest = OperatorFactory('BinaryAdd', "left op right".split(), add, add_repr)

class BinaryAdd(Operator):
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def execute(self):
        return self.left + self.right

    def add_repr(self):
        return str(self.left) + ' + ' + str(self.right)


class Assign(Operator):
    def __init__(self, **kwargs):
        self.names = kwargs['targets']
        value 

    def execute(self):
        if self.left
        return self.left = self.right

    def add_repr(self):
        return str(self.left) + ' + ' + str(self.right)