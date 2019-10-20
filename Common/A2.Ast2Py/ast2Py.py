import ast
import astor


if __name__ == '__main__':

    '''
    def fib():
        a = 0
        b = 1
        while True:            # First iteration:
            yield a            # yield 0 to start with and then
            a, b = b, a + b    # a will now be 1, and b will also be 1, (0 + 1)

    for i in fib():
        print(i)
        if i > 100:
            break
    '''
    # a = 0
    a_eq_0 = ast.Assign(targets=[ast.Name(id="a", ctx=ast.Store())],
                        value=ast.Num(0))
    # b = 0
    b_eq_1 = ast.Assign(targets=[ast.Name(id="b", ctx=ast.Store())],
                        value=ast.Num(1))

    # yield a
    yield_a = ast.Expr(value=ast.Yield(ast.Name(id="a", ctx=ast.Load())))

    # ----------------------------------------------------------------------------------
    # a, b = b, a + b
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

    # -------------------------------------------------------------------------------------

    '''
    while True:            # First iteration:
        yield a            # yield 0 to start with and then
        a, b = b, a + b    # a will now be 1, and b will also be 1, (0 + 1)
    '''

    while_body = [yield_a, assign1]
    whileLoop = ast.While(test=ast.NameConstant(value=True),
                          body=while_body,
                          orelse=[])

    '''
    def fib():
        a = 0
        b = 1
        while True:            # First iteration:
            yield a            # yield 0 to start with and then
            a, b = b, a + b    # a will now be 1, and b will also be 1, (0 + 1)

    '''
    fib_def = ast.FunctionDef(name="fib",
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
    fib_call = ast.Call(func=ast.Name(id="fib", ctx=ast.Load()),
                        args=[],
                        keywords=[])
    for_i = ast.For(target=ast.Name(id="i", ctx=ast.Store()),
                    iter=fib_call,
                    body=[print_i,
                          if_i],
                    orelse=[])

    as_tree = ast.Module(body=[fib_def, for_i])
    ast.fix_missing_locations(as_tree)
    print(astor.to_source(as_tree))

    program_string = astor.to_source(as_tree)
    exec(program_string)
