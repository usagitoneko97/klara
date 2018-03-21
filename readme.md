On every folder, the *example.py* is the python code that parse into ast for our exercises.

# Tools

## Ast viewer

To simplify the process of exploring the whole ast, [astviewer](https://github.com/titusjan/astviewer) is a simple gui perform the job. Detail instruction on installing astviewer can be found [here](https://github.com/titusjan/astviewer). 

![astViewer](https://github.com/titusjan/astviewer/raw/master/screen_shot.png)

## Transform ast to python source code

[Astor](http://astor.readthedocs.io/en/latest/) can convert ast to readable python source code. 

Example usage:
```python
astTree = ast.parse("b = 2\nc = 3\na = b + c\nd=b+c")
print(astor.to_source(astTree))
```

# Examples 
1. [printing of function name in ast](https://github.com/usagitoneko97/python-ast/tree/master/A1.FunctionDef)

2. [Ast to python code](https://github.com/usagitoneko97/python-ast/tree/master/A2.Ast2Py)

3. [Local Value Numbering](https://github.com/usagitoneko97/python-ast/tree/master/A3.LVN)