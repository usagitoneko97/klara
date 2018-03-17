import ast

def main():
    testContent = open("example.py").read()
    asTree = ast.parse(testContent, filename="temp.py")
    printFuncName(asTree.body)


def printFuncName(bodyList, indentation=""):
    """
    print all the name of the function def, including sub function
    :param body: a list of the body
    :param indentation: internal use for recursive
    """
    for node in bodyList:
        if isinstance(node, ast.FunctionDef):
            print("{}:{} {}".format(node.lineno, node.col_offset,
                                    indentation + node.name))
            printFuncName(node.body, indentation + "    ")

if __name__ == "__main__":
    main()


