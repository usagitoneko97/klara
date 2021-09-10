import sys
import ast


class ClassNameGetter(ast.NodeVisitor):
    def __init__(self):
        self.res = []

    def visit_ClassDef(self, node):
        self.res.append(node.name)


def main():
    fn = sys.argv[1]
    with open(fn, "r") as f:
        tree = ast.parse(f.read())
    cg = ClassNameGetter()
    cg.visit(tree)
    for res in cg.res:
        print(res + ",")


if __name__ == "__main__":
    main()
