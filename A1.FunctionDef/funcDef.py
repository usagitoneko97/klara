import ast

def main():
    test_content = open("example.py").read()
    asTree = ast.parse(test_content, filename="temp.py")
    asTree = link_parent_node(asTree)

    print_func_name(asTree.body)



def link_parent_node(root):
    """
    visit all the node to link them to their parent
    :param root: the asTree root
    :return: added attr parent and return the as tree
    """
    for node in ast.walk(root):
        for child in ast.iter_child_nodes(node):
            child.parent = node

    return root

def print_func_name(body_list, indentation=""):
    """
    print all the name of the function def, including sub function
    :param body: a list of the body
    :param indentation: internal use for recursive
    """
    for node in body_list:
        if isinstance(node, ast.FunctionDef):
            parent_name = ""
            if isinstance(node.parent, ast.FunctionDef):
                # it has a parent
                parent_name = "(parent : " + node.parent.name + ")"
            print("{}:{} {} {}".format(node.lineno, node.col_offset,
                                    indentation + node.name, parent_name))
            print_func_name(node.body, indentation + "    ")

if __name__ == "__main__":
    main()


