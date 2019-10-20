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