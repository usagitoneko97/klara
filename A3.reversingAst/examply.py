def fib_recursive(startNumber, endNumber):
    n = 0
    cur = f(n)
    while cur <= endNumber:
        if startNumber <= cur:
            print(cur)
        n += 1
        cur = f(n)

def fib_iterative(startNumber, endNumber):
    for cur in F():
        if cur > endNumber: return
        if cur >= startNumber:
            yield cur

for i in fib_iterative(10, 200):
    print(i)
