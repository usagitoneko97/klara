import ast

def main():
    testContent = open("example.py").read()
    asTree = ast.parse(testContent, filename="temp.py")
    printFuncName(asTree.body)


def printFuncName(body, indentation=""):
    """
    print all the name of the function def, including sub function
    :param body: a list of the body
    :param indentation: internal use for recursive
    """
    for stmt in body:
        if isinstance(stmt, ast.FunctionDef):
            print(indentation + stmt.name)
            printFuncName(stmt.body, indentation + "    ")

if __name__ == "__main__":
    main()


