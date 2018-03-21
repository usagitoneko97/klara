# 1. printing of function name in ast

## 1.1 objective
Given the python code, *example.py*:

```python
def decorator_ex(some_func):
    """
    this is a decorator example
    """

    def wrapper():
        def some_func():
            pass
        pass

    return wrapper

@decorator_ex
def foo():
    pass

some_statement = 1 + 2
anotherStatement = some_statement
```
and the ast representation as below:

![astView](https://github.com/usagitoneko97/python-ast/blob/master/A1.FunctionDef/resources/astViewer.svg)

The aim is to print out all the function def's name, respective lineno and column offset, including the sub function with the correct indentation. Example output:
```python
>>> 1:0 decorator_ex
>>> 6:4    wrapper
>>> 7:8        some_func
>>> 13:0 foo
```

## 1.2 The program
Before doing our analysis, an ast has to be parsed and build that based on *example.py*. 
```python
# read the content of the example.py
test_content = open("example.py").read()
# build the ast
as_tree = ast.parse(test_content, filename="temp.py")
```
To print only the parent function, it was simply done by iterate through the **list of the body** and locate only the `ast.FunctionDef` instance. 
```python
for node in as_tree.body:
    if isinstance(node, ast.FunctionDef):
        print(node.name)
```
To print also the sub function, the obvious and easiest way is to recursive call itself whenever the body is in `ast.FunctionDef` type.
```python
def print_func_name(bodyList):
    for node in bodyList:
        if isinstance(node, ast.FunctionDef):
            print(node.name)
            print_func_name(node.body)
```
The final part is to add in the *indentation* of the sub function. It can be done easily by defining another parameter in the `print_func_name` function. The full working python code is shown below:
```python
def main():
    test_content = open("example.py").read()
    as_tree = ast.parse(test_content, filename="temp.py")
    print_func_name(as_tree.body)

def print_func_name(bodyList, indentation=""):
    for node in bodyList:
        if isinstance(node, ast.FunctionDef):
            print("{}:{} {}".format(node.lineno, node.col_offset,
                                    indentation + node.name))
            print_func_name(node.body, indentation + "    ")

if __name__ == "__main__":
    main()
```

## 1.3 Additional
### 1.3.1 Get the parent of ast node
Suppose we wanted to find the parent function that associates with that subfunction. But there is no attribute on the node that links back to its parent. If it is needed, the node can be augmented with that information. The following code shows how *[[1]](https://stackoverflow.com/questions/34570992/getting-parent-of-ast-node-in-python)*:
```python
for node in ast.walk(root):
    for child in ast.iter_child_nodes(node):
        child.parent = node
```

Attribute `parent` then can be used by:
```python
if isinstance(node.parent, ast.FunctionDef):
    # it has a parent of type FunctionDef
    parentName = "(parent : " + node.parent.name + ")"
```

The result
```python
>>> 1:0 decorator_ex
>>> 6:4    wrapper  (parent : decorator_ex)
>>> 7:8        some_func  (parent : wrapper)
>>> 13:0 foo
```

## 1.4 Reference
1. https://stackoverflow.com/questions/34570992/getting-parent-of-ast-node-in-python
2. [official python ast doc](https://docs.python.org/2/library/ast.html)
3. [greentreesnakes enhanced python ast doc](http://greentreesnakes.readthedocs.io/en/latest/index.html)
