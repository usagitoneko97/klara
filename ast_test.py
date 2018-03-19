import ast

globalStr = ''
class stringLister(ast.NodeVisitor):
    def visit_Name(self, node):
        global globalStr
        print(node.id)
        globalStr = node
        self.generic_visit(node)

    def visit_Assign(self, node):
        print(node.value.s)
        self.generic_visit(node)

class stringModifier(ast.NodeTransformer):

    def visit_List(self, node):
        print("someghing")

if __name__ == "__main__":
    tree = ast.parse("firstStr = 'str' \nsecondStr = 'str2'")
    # byteCode = compile(tree, filename="<ast>", mode="exec")
    # exec(byteCode)
    node = stringModifier().visit(tree)
    # stringLister().visit(tree)

    # node = stringLister().visit(tree)


