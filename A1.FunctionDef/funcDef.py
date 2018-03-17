import ast

def main():
    testContent = open("example.py").read()
    asTree = ast.parse(testContent, filename="temp.py")
    asTree = linkParentNode(asTree)

    printFuncName(asTree.body)



def linkParentNode(root):
    """
    visit all the node to link them to their parent
    :param root: the asTree root
    :return: added attr parent and return the as tree
    """
    for node in ast.walk(root):
        for child in ast.iter_child_nodes(node):
            child.parent = node

    return root

def printFuncName(bodyList, indentation=""):
    """
    print all the name of the function def, including sub function
    :param body: a list of the body
    :param indentation: internal use for recursive
    """
    for node in bodyList:
        if isinstance(node, ast.FunctionDef):
            parentName = ""
            if isinstance(node.parent, ast.FunctionDef):
                # it has a parent
                parentName = "(parent : " + node.parent.name + ")"
            print("{}:{} {} {}".format(node.lineno, node.col_offset,
                                    indentation + node.name, parentName))
            printFuncName(node.body, indentation + "    ")

if __name__ == "__main__":
    main()


