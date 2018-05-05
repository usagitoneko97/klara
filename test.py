class Stack:
    def __init__(self, i=None):
        if i is not None:
            self.items = [i]
        else:
            self.items = []

    def isEmpty(self):
        return self.items == []

    def push(self, item):
        self.items.append(item)

    def pop(self):
        return self.items.pop()

    def remove(self, item):
        self.items.remove(item)

    def peek(self):
        return self.items[len(self.items) - 1]

    def size(self):
        return len(self.items)


s = Stack()
s.push(0)
s.push(1)
s.push(5)
s.push(3)
s.remove(5)
pass
