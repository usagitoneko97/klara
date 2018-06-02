# 1. Software and libraries requirements
Python3.5.2 is used and below is the libraries and GUI that may be used in topics in section [2](https://github.com/usagitoneko97/python-ast#2-topics)
## 1.2 Ast viewer

To simplify the process of exploring the whole ast, [astviewer](https://github.com/titusjan/astviewer) is a simple gui perform the job. Detail instruction on installing astviewer can be found [here](https://github.com/titusjan/astviewer). 

![astViewer](https://github.com/titusjan/astviewer/raw/master/screen_shot.png)

## 1.3 Transform ast to python source code

[Astor](http://astor.readthedocs.io/en/latest/) can convert ast to readable python source code. 

Example usage:
```python
ast_tree = ast.parse("b = 2\nc = 3\na = b + c\nd=b+c")
print(astor.to_source(ast_tree))
```

# 2. Topics 
1. [Printing of Function Name in Ast](A1.FunctionDef)

2. [Ast to Python code](A2.Ast2Py)

3. [Local Value Numbering](A3_LVN)

4. [Control Flow Graph](A4_CFG)
