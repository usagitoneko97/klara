import ast
import astor


if __name__ == '__main__':
    # x = 1 + 2

    lhsNode = ast.Name(id="x", ctx=ast.Store())
    # create number 1
    num1 = ast.Num(n=1)

    # create number 2
    num2 = ast.Num(4)

    addOp = ast.BinOp(left=num1, op=ast.Add(), right=num2)

    assignNode = ast.Assign(targets=[lhsNode], value=addOp)

    asTree = ast.Module(body=[assignNode])

    # add in the missing line no
    ast.fix_missing_locations(asTree)

    print(astor.to_source(asTree))
