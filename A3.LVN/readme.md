# Introduction to Local Value Numbering (LVN)
Consider the following statements
```python
a = b + c
d = a - b
e = b + c
```
The expression `b + c` is redundant in the 3rd line of the assignment since `b + c` is already computed in the first assignment and no intervening operation redefines the arguments. The compiler should rewrite this block so `b + c` only have to compute once. 
```python
a = b + c
d = a - d
e = a
```
One of the techniques is **Local Value Numbering**. 

## The algorithm
This algorithm is able to solve the problem mention above. But there is a limitation. .....

example (indirect substitution) that this algorithm will not be able to solve
a = b + c
d = b
e = d + c

a = b + c
d = b
e = a


a = c + 5 * y ^ 7
b = 5 * y
d = c + 5 * y ^ 7

However, Static Single Assignment (SSA) [1][2] can solve this. (More research/exploration needed here.)

![lvnFirst](https://github.com/usagitoneko97/python-ast/blob/master/A2.LVN/resources/lvnFirst.svg)

Consider the example in the introduction. The algorithm parses through the expression and enumerate each variable, and adds it to a Python `dictionary`. Variables already added will not be added again. The dictionary is used for searching purpose later.


~~In the first operation, the variables on the right-hand side will get the value number first, either previously defined, or assigning new value number.~~





LVN then constructs the textual string **"0 + 1"** as a hash key to perform a lookup. It will fail since there is no previous insertion. LVN then creates an entry of **"0 + 1"** and assigns the value to `"a"`. The final step for one expression is to create an entry for the variable at the left-hand side. *Keep in mind that variable(s) at the left-hand side will always be assigned a new value number.* That is, LVN creates an entry for `"a"` and assigns new value number namely `2`. 

Moving on the second expression, LVN will perform the same step as above. 

![lvnSecond](https://github.com/usagitoneko97/python-ast/blob/master/A2.LVN/resources/lvnSecond.svg)

Because of textual string `"2 - 3"` is not found in the hashmap, it will perform the exact step as above. 

On the third expression, 

![lvnThird](https://github.com/usagitoneko97/python-ast/blob/master/A2.LVN/resources/lvnThird.svg)

Now because of string `"0 + 1"` is found in the hash, LVN will replace the expression on the right with the result of `"0 + 1"`, namely a.

![lvnReplaced](https://github.com/usagitoneko97/python-ast/blob/master/A2.LVN/resources/lvnReplaced.svg)

## The python implementation
To get started easily, consider the only assignment of binary operation, (`binOp` in python ast)
### Data structure and local variable used
For the sake of simplicity, we will use **2 hash map** (dictionary in python), 1 for storing the corresponding value number to the variable, and 1 for storing the textual string like `"2 - 3"`. We also need a local variable to keep track of the currently assigned value number. 

### Dealing with an abstract syntax tree
There is 3 ast node that we should look out for. 

---

`Assign` is basically any assignment of variables. And is the parent node of the remaining 2 nodes. 

**Attr** :  
- `Targets` - is a list of node representing the left-hand side variable(s)
- `value` - is a single node on the right-hand side. For our example, it could be either *BinOp* or *Name*.  
Eg.
```python
a = b + c
b = 1
c = foo()
```
- `BinOp` is any binary operation.

    **Attr** :
    - `left` : left side of the operator
    - `op` : the operator. Eg. "+", "-", "*"
    - `right` : the right side of the operator
 Eg.
```python
b + c
c - d
d * s
```
- `Name` could be child of *Assign* or child of *BinOp*. `Name` is a string that represents a variable name.

    **Attr** :
    - `id` : the string of the variable name
    - `ctx` : the context of the variable. (store, load, del)
Eg. 
```python
b
c
d
```

### Pseudocode
```python
def lvnOptimize(asTree)
    for assignNode in getAssignNodeClass(asTree):
    if assignNode.value is BinOp:
        # assign or locate the right hand side of assignment
        # the value number on the dict
        valNumLeft = addToValueDict(assignNode.value.left.id)
        valNumRight = addToValueDict(assignNode.value.right.id)
        # build something like "2Add3"
        queryString = valNumLeft + assignNode.value.op.__class__.__name__ +
                        valNumRight

        if queryString not in lvnDict:
            #add entry of querystring in lvn Dict with the value of lhs var name
        else:
            # It is in, replace the binop with a single variable
            nameNode = ast.Name()
            nameNode.id = self.lvnDict[queryString]
            nameNode.ctx = ast.Store()
            assignNode.value = nameNode
    
    # Always assign the new value number on the lhs of assign class
    Add assignNode.targets[0].id to valueDict
    currentVal += 1
    return asTree
```

The full python source code can be found [here](https://github.com/usagitoneko97/python-ast/blob/master/A2.LVN/lvn.py)

## References
- Torczon, L. and Cooper, M. ed., (2012). Ch8 - Introduction to optimization. In: Engineering a compiler, 2nd ed. Texas: Elsevier, Inc, pp.420-428.
