import ast

class lvn:
    def __init__(self):
        self.valueDict = dict()
        self.lvnDict = dict()
        self.currentVal = 0
    def assignValueNumber(self, asTree):
        for assignNode in self.getAssignClass(asTree):
            # check if its normal assignment or bin op
            if isinstance(assignNode.value, ast.BinOp):
                queryString = ""
                queryString += str(self.addToValueDict(assignNode.value.left.id))
                queryString += assignNode.value.op.__class__.__name__
                queryString += str(self.addToValueDict(assignNode.value.right.id))

                if queryString not in self.lvnDict:
                    # number 3 is dummy
                    self.lvnDict[queryString] = 3
                else:
                    # it's in, replace the BinOp node with name
                    pass
                self.valueDict[assignNode.targets[0].id] = self.currentVal
                self.currentVal += 1

            elif isinstance(assignNode.value, ast.Num):
                # check var exits in the valueDict (assume target always 1)
                self.valueDict[assignNode.targets[0].id] = self.currentVal
                self.currentVal += 1

    def getAssignClass(self, asTree):
        for i in range(len(asTree.body)):
            if isinstance(asTree.body[i], ast.Assign):
                yield asTree.body[i]

    def addToValueDict(self, string):
        if string not in self.valueDict:
            self.valueDict[string] = self.currentVal
            self.currentVal += 1

        return self.valueDict[string]