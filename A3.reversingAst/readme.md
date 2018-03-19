# Reversing ast
The aim is to build an ast from scratch, a string of python code can then be generated from ast, and finally execute it. 

## Run the program

```sh
$ cd A3.reversingAst
$ python reverseAst.py
```

## Building an ast
Consider the python code that generates fibonacci series below
```python
def fib():
    a = 0
    b = 1
    while True:            # First iteration:
        yield a            # yield 0 to start with and then
        a, b = b, a + b    # a will now be 1, and b will also be 1, (0 + 1)

for i in fib():
    print(i)
    if i > 100:
        break
```

To start building the ast, it's recommended to use [pyastviewer](https://github.com/titusjan/astviewer) to get an idea how the hierachy of the ast looks like. 

![astviewer](https://github.com/usagitoneko97/python-ast/blob/master/A3.reversingAst/resources/astviewer.svg)

### introduction to build an ast
[Documentation](https://greentreesnakes.readthedocs.io/en/latest/nodes.html) here describe every class in details.

Assume we want to build a complete source code with just a **expression** and a **statement** :
```python
a = 3 #statement
print(a) #expression
```
The class of a variable is called `Name` that have attributes `id` and `ctx`. 

The attributes `id` is referring to the var name while `ctx` can be one of the following types:

- Load : is used when var is meant to be loaded. *eg.* :  *yield a*
- Store : is used when var is updated to a new value: *eg : a = 3*
- Del : is used when var is meant to be deleted. *eg : del a*

```python
# This represent variable *a*
var_a = ast.Name(id="a", ctx=ast.Load())
# This represent value 3
val_3 = ast.Num(n=3)
# print(a) is calling the function print with parameter a
printCall = ast.Call(func=ast.Name(id="print", ctx=ast.Load()),
                     args=[ast.Name(id="i", ctx=ast.Load())],
                     keywords=[])
```

In a particular line of a python code, it can be either `expression` or a `statement`. In the case above, *a = 3* is a statement. Therefore *var_a* and *val_3* has to wrap inside an `Assign` class. *print(a)* is a `expression`, therefore it has to be wrap in `Expr` class. 
```python
a_eq_3 = ast.Assign(targets=[var_a], value=val_3)
print_a = ast.Expr(value=printCall)
```
 
To make this tree complete, the whole thing has to wrap inside a class called `Module`. Module represents every line of statement or expression and is the highest hierachy in an ast. 
```python
as_tree = ast.Module(body=[a_eq_3, print_a])
```
This step below is to assign the line number and the column offset for each node. Eventhough it's optional to do that but it's still preferably to do so.
```python
ast.fix_missing_locations(as_tree)
```
The final step is to convert the ast into python source code and execute it. [astor](http://astor.readthedocs.io/en/latest/) is a library that can perform the job.
```python
program_string = astor.to_source(as_tree)
exec(program_string)
```
The console should displayed following if all the steps is perform correctly. 
```python
>>> 3
```
---
### Building ast for a fibonacci series
