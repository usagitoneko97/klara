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
    def fib():
        a = 0
        b = 1
        while True:            # First iteration:
            yield a            # yield 0 to start with and then
            a, b = b, a + b    # a will now be 1, and b will also be 1, (0 + 1)
    '''
    # a = 0
    a_eq_0 = ast.Assign(targets=[ast.Name(id="a", ctx=ast.Store())],
                       value=ast.Num(0))
    b_eq_1 = ast.Assign(targets=[ast.Name(id="b", ctx=ast.Store())],
                       value=ast.Num(1))

    # yield a
    yield_a = ast.Expr(value=ast.Yield(ast.Name(id="a", ctx=ast.Load())))

    # a, b
    left_target = [ast.Tuple(elts=[ast.Name(id="a", ctx=ast.Store()),
                                   ast.Name(id="b", ctx=ast.Store())],
                             ctx=ast.Load())]

    # b, a + b
    right_value = ast.Tuple(elts=[ast.Name(id="b", ctx=ast.Store()),
                                   ast.BinOp(left=ast.Name(id="a", ctx=ast.Load()),
                                             op=ast.Add(),
                                             right=ast.Name(id="b", ctx=ast.Load()))],
                            ctx=ast.Load())

    # a, b = b, a + b
    assign1 = ast.Assign(targets=left_target, value=right_value)

    '''
    while True:            # First iteration:
        yield a            # yield 0 to start with and then
        a, b = b, a + b    # a will now be 1, and b will also be 1, (0 + 1)
    '''

    while_body = [yield_a, assign1]
    whileLoop = ast.While(test=ast.NameConstant(value=True),
                          body=while_body,
                          orelse=[])



    fibDef = ast.FunctionDef(name="fib",
                             args=ast.arguments(args=[],
                                                vararg=None,
                                                kwonlyargs=[],
                                                kw_defaults=[],
                                                kwarg=None,
                                                defaults=[]),
                             body=[a_eq_0,
                                   b_eq_1,
                                   whileLoop],
                             decorator_list=[],
                             returns=None)

    # print(i)
    print_i = ast.Expr(value=ast.Call(func=ast.Name(id="print", ctx=ast.Load()),
                                      args=[ast.Name(id="i", ctx=ast.Load())],
                                      keywords=[]))

    # if i > 100:
    #    break
    if_i = ast.If(test=ast.Compare(left=ast.Name(id="i", ctx=ast.Load()),
                                   ops=[ast.Gt()],
                                   comparators=[ast.Num(100)]),
                  body=[ast.Break()],
                  orelse=[])
    '''
    for i in fib():
        print(i)
        if i > 100:
            break
    '''

    # fib()
    fibCall = ast.Call(func=ast.Name(id="fib", ctx=ast.Load()),
                       args=[],
                       keywords=[])
    for_i = ast.For(target=ast.Name(id="i", ctx=ast.Store()),
                    iter=fibCall,
                    body=[print_i,
                          if_i],
                    orelse=[])

    asTree = ast.Module(body=[fibDef, for_i])
    ast.fix_missing_locations(asTree)
    print(astor.to_source(asTree))

    programString = astor.to_source(asTree)
    exec(programString)
