# printing of function name in ast

## objective
Given the python code, *example.py*:

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

someStatement = 1 + 2
anotherStatement = someStatement
```
and the ast representation as below:

![astView](https://github.com/usagitoneko97/python-ast/blob/master/A1.FunctionDef/resources/astViewer.svg)

The aim is to print out all the function def's name, respective lineno and column offset, including the sub function with the correct indentation. Example output:
```python
>>> 1:0 decoratorEx
>>> 6:4    wrapper
>>> 7:8        someFunc
>>> 13:0 foo
```

## The program
Before doing our analysis, we need to parse and build our ast based on *example.py*.
```python
# read the content of the example.py
testContent = open("example.py").read()
# build the ast
asTree = ast.parse(testContent, filename="temp.py")
```
Let us start by printing only the parent function. It was simply done by iterate through the **list of the body** and locate only the `ast.FunctionDef` instance. 
```python
for node in asTree.body:
    if isinstance(node, ast.FunctionDef):
        print(node.name)
```
To print also the sub function, the obvious and easiest way is to recursive call itself whenever the body is in `ast.FunctionDef` type.
```python
def printFuncName(bodyList):
    for node in bodyList:
        if isinstance(node, ast.FunctionDef):
            print(node.name)
            printFuncName(node.body)
```
The final part is to add in the *indentation* of the sub function. It can be done easily by defining another parameter in the `printFuncName` function. The full working python code is shown below:
```python
def main():
    testContent = open("example.py").read()
    asTree = ast.parse(testContent, filename="temp.py")
    printFuncName(asTree.body)

def printFuncName(bodyList, indentation=""):
    for node in bodyList:
        if isinstance(node, ast.FunctionDef):
            print("{}:{} {}".format(node.lineno, node.col_offset,
                                    indentation + node.name))
            printFuncName(node.body, indentation + "    ")

if __name__ == "__main__":
    main()
```

## Additional
### Get the parent of ast node
Assume that we want to print out the parent function def, we will want to find out the parent of the child node. (obviously there is other ways of printing the parent function def but let us assume that this is the only way)
Due to no attribute on a node that can link to parent node, we have to create it ourself by visiting all the node to manually link them. *[[1]](https://stackoverflow.com/questions/34570992/getting-parent-of-ast-node-in-python)*
```python
for node in ast.walk(root):
    for child in ast.iter_child_nodes(node):
        child.parent = node
```
We can then use the attribute `parent`
```python
if isinstance(node.parent, ast.FunctionDef):
    # it has a parent of type FunctionDef
    parentName = "(parent : " + node.parent.name + ")"
```
The result
```python
>>> 1:0 decoratorEx
>>> 6:4    wrapper  (parent : decoratorEx)
>>> 7:8        someFunc  (parent : wrapper)
>>> 13:0 foo
```

## Reference
1. https://stackoverflow.com/questions/34570992/getting-parent-of-ast-node-in-python
2. [official python ast doc](https://docs.python.org/2/library/ast.html)
3. [greentreesnakes enhanced python ast doc](http://greentreesnakes.readthedocs.io/en/latest/index.html)