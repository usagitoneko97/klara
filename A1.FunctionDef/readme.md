# Print all the function in the ast

## objective
Given the python code:

```python
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
```
and the ast representation as below:
![astView](https://github.com/usagitoneko97/python-ast/A1.FunctionDef/resources/astViewer.svg)


