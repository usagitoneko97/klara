import ast

def main():
    testContent = open("example.py").read()
    astTree = ast.parse(testContent, filename="test.py")
    printFuncName(astTree.body)


def printFuncName(body, indentation=""):
    for stmt in body:
        if isinstance(stmt, ast.FunctionDef):
            print(indentation + stmt.name)
            printFuncName(stmt.body, indentation + "    ")

if __name__ == "__main__":
    main()


