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

    '''
def fib_recursive(startNumber, endNumber):
    n = 0
    cur = f(n)
    while cur <= endNumber:
        if startNumber <= cur:
            print cur
        n += 1
        cur = f(n)
    '''
    # n = 0
    
    assign1 = ast.Assign(targets=ast.Name(id="x", ctx=ast.Store()),
                         value=ast.Num(0))
    
    assign1 = ast.Assign(targets=ast.Name(id="cur", ctx=ast.Store()),
                         value=ast.Call(func=ast.Name(id='f', ctx=ast.Store()),
                                        args=[ast.Name(id='n', ctx=ast.Store())],
                                        keywords=[]))
    '''
    while1 = ast.While(test=ast.Compare(left=ast.Name(id='cur', ctx=ast.Load()),
                                        opst=[ast.LtE()],
                                        comparators=[id="endNumber", ctx=ast.Load()],),
                       body=[ast.If(test=ast.Compare(left=ast.name("startNumber"), ctx=ast.Load(),
                                                     opst=[ast.LtE()],
                                                     comparators=[ast.Name("cur"), ctx=ast.Load()],),
                                    body=ast.Expr(ast.Call(func=ast.Name(id="print", ctx=ast.Load()),
                                                           args=[ast.Name(id="cur", ctx=ast.Load())],
                                                           keywords=[])),
                                    orelse=[]),
                             ast.AugAssign(target=ast.Name(id="n", ctx=ast.Store()),
                                           op=ast.Add(),
                                           value=ast.Num(1)),
                             ast.Assign(targets=[ast.Name(id="cur", ctx=ast.Store())],
                                        value=ast.Call(func=ast.Name(id="f", ctx=ast.Load()),
                                                       args=[ast.Name(id="n", ctx=ast.Load())],
                                                       keywords=[]))],
                       orelse=[])
    funcDef = ast.FuncDef(name="fib_recursive",
                          args=ast.Args(args=[ast.arg(arg="startNumber",
                                                      annotation=None),
                                              asr.arg(arg="endNumber",
                                                      annotation=None)],
                                        vararg=None)

                          body=[])

    '''
    # cur = f(n)
    cur=[ast.Name(id="cur", ctx=ast.Store())]
    fib=ast.Call(func=ast.Name(id="fib", ctx=ast.Load())
    n=[ast.Name(id="n", ctx=ast.Load())]               
    curAssign = ast.Assign(cur, fib, n)
    
'''
def fib_iterative(startNumber, endNumber):
    for cur in F():
        if cur > endNumber: return
        if cur >= startNumber:
            yield cur

for i in fib_iterative(10, 200):
    print i
    '''
    
    

