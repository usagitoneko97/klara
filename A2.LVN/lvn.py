import ast

class lvn:
    def __init__(self):
        self.valueDict = dict()
        self.lvnDict = dict()
        self.currentVal = 0

    def lvnOptimize(self, asTree):
        """
        perform lvn analysis on the asTree and return an optimized tree
        :param asTree: the root of the tree
        :return: optimized tree
        """
        for assignNode in self._getAssignClass(asTree):
            # check if its normal assignment or bin op
            if isinstance(assignNode.value, ast.BinOp):
                # form a string in form of "<valueNumber1><operator><valueNumber2>
                queryString = ""
                queryString += str(self._addToValueDict(assignNode.value.left.id))
                queryString += assignNode.value.op.__class__.__name__
                queryString += str(self._addToValueDict(assignNode.value.right.id))

                if queryString not in self.lvnDict:
                    self.lvnDict[queryString] = assignNode.targets[0].id
                else:
                    # it's in, replace the BinOp node with name
                    nameNode = ast.Name()
                    nameNode.id = self.lvnDict[queryString]
                    nameNode.ctx = ast.Store()
                    assignNode.value = nameNode

            # always assign new value number to left hand side
            self.valueDict[assignNode.targets[0].id] = self.currentVal
            self.currentVal += 1

        return asTree

    @staticmethod
    def _getAssignClass(asTree):
        for i in range(len(asTree.body)):
            if isinstance(asTree.body[i], ast.Assign):
                yield asTree.body[i]

    def _addToValueDict(self, string):
        if string not in self.valueDict:
            self.valueDict[string] = self.currentVal
            self.currentVal += 1

        return self.valueDict[string]