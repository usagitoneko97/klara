def dummy1():
    dummy2()

def dummy2():
    pass

x = 1
y = 0
if x == 1:
    y = 1
else:
    y = 2

dummy1()
