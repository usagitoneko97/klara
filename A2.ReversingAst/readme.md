# Reversing ast
The aim is to build an ast from scratch, a string of Python code can then be generated from ast, and finally execute it. 

## Run the program

```sh
$ cd A2.ReversingAst
$ python reverseAst.py
```

## Building an ast

### Introduction to building an ast
[Documentation](https://greentreesnakes.readthedocs.io/en/latest/nodes.html) here describe every class in details.

Suppose we want to build a complete source code with just a **expression** and a **statement** :
```python
a = 3 #statement
print(a) #expression
```
The class of a variable is called `Name` that have attributes `id` and `ctx`. 

The attributes `id` is referring to the var name while `ctx` can be one of the following types:

- Load: is used when var is meant to be loaded. *eg.* :  *yield a*
- Store: is used when var is updated to a new value: * eg: a = 3*
- Del: is used when var is meant to be deleted. * eg: del a*

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
 
To make this tree complete, the whole thing has to wrap inside a class called `Module`. A module represents every line of statement or expression and is the highest hierarchy in an ast. 
```python
as_tree = ast.Module(body=[a_eq_3, print_a])
```
This step below is to assign the line number and the column offset for each node. Even though it's optional to do that but it's still prefer to do so.
```python
ast.fix_missing_locations(as_tree)
```
The final step is to convert the ast into python source code and execute it. [astor](http://astor.readthedocs.io/en/latest/) is a library that can perform the job.
```python
program_string = astor.to_source(as_tree)
exec(program_string)
```
The console should display following if all the steps are perform correctly. 
```python
>>> 3
```
---
### Building ast for a Fibonacci series
Consider the python code that generates Fibonacci series below
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

To start building the ast, it's recommended to use [pyastviewer](https://github.com/titusjan/astviewer) to get an idea how the hierarchy of the ast looks like. 

![astviewer](https://github.com/usagitoneko97/python-ast/blob/master/A2.ReversingAst/resources/astviewer.svg)

To get an idea how to start, it's often good to build the statement or expression inside a function or a for/while loop etc.. 1 by 1. For example, assume **def fib()** is to be build, **a = 0**, **b = 1**, **yield a**, **a, b= b, a+b** has to be build first.
```python
# a = 0
a_eq_0 = ast.Assign(targets=[ast.Name(id="a", ctx=ast.Store())],
                    value=ast.Num(0))
# b = 0
b_eq_1 = ast.Assign(targets=[ast.Name(id="b", ctx=ast.Store())],
                    value=ast.Num(1))

# yield a
yield_a = ast.Expr(value=ast.Yield(ast.Name(id="a", ctx=ast.Load())))

# a, b = b, a + b
# a, b
left_target = [ast.Tuple(elts=[ast.Name(id="a", ctx=ast.Store()),
                                ast.Name(id="b", ctx=ast.Store())],
                            ctx=ast.Load())]

# b, a + b
right_value = ast.Tuple(elts=[ast.Name(id="b", ctx=ast.Store()),
                                ast.BinOp(left=ast.Name(id="a", ctx=ast.Load()),
                                            op=ast.Add(),
                                            right=ast.Name(id="b", ctx=ast.Load()))],
                        ctx=ast.Load())

# a, b = b, a + b
assign1 = ast.Assign(targets=left_target, value=right_value)
```

After that, **yield a**, **a, b= b, a+b** is added inside a while loop class. 
```python
while_body = [yield_a, assign1]
whileLoop = ast.While(test=ast.NameConstant(value=True),
                        body=while_body,
                        orelse=[])

```

Then **a = 0**, **b = 1** along with the whole while loop is added inside a FunctionDef class.
```python
fib_def = ast.FunctionDef(name="fib",
                          args=ast.arguments(args=[],
                                             vararg=None,
                                             kwonlyargs=[],
                                             kw_defaults=[],
                                             kwarg=None,
                                             defaults=[]),
                          body=[a_eq_0,
                                b_eq_1,
                                whileLoop],
                          decorator_list=[],
                          returns=None)
```

Building the *for loop* will be using the same techniques described above. 

After **def fib()** and the **for loop** has been build, the ast can be completed, printed, and executed by:

```python
as_tree = ast.Module(body=[fib_def, for_i])
ast.fix_missing_locations(as_tree)
print(astor.to_source(as_tree))

program_string = astor.to_source(as_tree)
exec(program_string)
```

Upon executing, console should shows
```python
>>> 0
>>> 1
>>> 1
>>> 2
>>> 3
>>> 5
>>> 8
>>> 13
>>> 21
>>> 34
>>> 55
>>> 89
>>> 144
```