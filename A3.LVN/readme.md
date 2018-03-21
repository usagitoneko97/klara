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

### Assumption
The algorithm can only accept simple expression with a maximum of 3 variables and at most 1 operator (excluding `equal` operator), which is known as **Three-Address Code** (TAC) [give a link]. E.g.,
```
a = b + c * d              # Not acceptable
e = f + g                  # Acceptable
```

However, this does not make the algorithm **useless** because the complex expression can be broken down into several simpler TAC for ease of analysis. E.g.,
```
# a = b + c * d becomes:
z = c * d                  # z is a temporal variable
a = b + z
```
Also compiler optimization often emits machine code, which matches the TAC form. E.g.,
```
# a = b + c * d              ARM code 
z = c * d                  # MUL R0, R1, R2         ; Assuming R0 = z, R1 = c, R2 = d
a = b + z                  # ADD R3, R4, R0         ; Assuming R3 = a, R4 = b
```

### Limitations
This algorithm is able to solve the problem mention above. But there is a limitation. .....

example (indirect substitution) that this algorithm will not be able to solve
```python
# [Code 1]
# Input
a = b + c
d = b
e = d + c

# LVN output
a = b + c
d = b
e = d + c            # Fail to substitute

# Expected output
a = b + c
d = b
e = a
```
```python
# [Code 2]
a = c + 5 * y ^ 7
b = 5 * y
d = c + 5 * y ^ 7
```
However, Static Single Assignment (SSA) [1][2] can solve this. (More research/exploration needed here.)


### Algorithm in details

Consider the example in the introduction. The algorithm parses through the expression and enumerate each variable, and adds it to a Python `dictionary`. *Keep in mind that variable(s) at the left-hand side will always be assigned after the right-hand side has been assigned a new value number.*Variables already added will not be added again. The dictionary is used for searching purpose later. The following diagrams show how it's enumerated. 

![lvnFirst](https://github.com/usagitoneko97/python-ast/blob/master/A3.LVN/resources/lvnFirst.svg)

![lvnSecond](https://github.com/usagitoneko97/python-ast/blob/master/A3.LVN/resources/lvnSecond.svg)


![lvnThird](https://github.com/usagitoneko97/python-ast/blob/master/A3.LVN/resources/lvnThird.svg)

LVN then constructs the textual string on the first statement **"0 + 1"** as a hash key to perform a lookup. It will fail since there is no previous insertion. LVN then creates an entry of **"0 + 1"** and assigns the value number correspond to `"a"`.

![lvnFirstHash](https://github.com/usagitoneko97/python-ast/blob/master/A3.LVN/resources/lvnFirstHash.svg)

Because of textual string `"2 - 3"` is not found in the hashmap, it will also insert into the dictionary. 

![lvnSecondHash](https://github.com/usagitoneko97/python-ast/blob/master/A3.LVN/resources/lvnSecondHash.svg)


On the third expression, 


Now because of string `"0 + 1"` is found in the hash, LVN will replace the expression on the right with the result of `"0 + 1"`, namely a.

![lvnThirdHash](https://github.com/usagitoneko97/python-ast/blob/master/A3.LVN/resources/lvnThirdHash.svg)

![lvnReplaced](https://github.com/usagitoneko97/python-ast/blob/master/A3.LVN/resources/lvnReplaced.svg)

## Problems in LVN
### Choice of names
Consider the code below:
```python
# code                expected result
# -------------------------------------
a = x + y                       
b = x + y            # b = a   
a = 17               # Redefining `a` as 17                
c = x + y            # c = b since that c != a = 17
```
~~With the understanding on the section above, the second statement will be substituted by a.~~
but LVN produces the following non-optimized result though correct:

```python
a = x + y
b = a
a = 17
c = x + y            # Fail to optimize this statement
```

But the 3rd statement redefined `"a"`, thus modifies value number of `"a"` from **2** to **4** . On the 4th statement, it again discovers that `"x + y"` is redundant, but it cannot substitute with Value Number 2 since `"a"` does not carry Value Number 2 anymore. 

One way to solve this efficiently is by using `Static Single Assignment (SSA)`. After transforming the code to SSA form, 

![ssaExampel](https://github.com/usagitoneko97/python-ast/blob/master/A3.LVN/resources/ssaExample.svg)

With these new names defined, LVN can then produces the desired result. To be exact, `"x + y"` in the 4th assignment is now replaced by a<sub>0</sub>. An implementation will then map the a<sub>1</sub> to the original `a` and then declares a new temporary variable to hold a<sub>0</sub>

> temp = x + y                        
> b = temp             
> a = 17                
> c = temp   


## The python implementation
To get started easily, consider the only assignment of binary operation, (`binOp` in python ast)
### Data structure and local variable used
For the sake of simplicity, **2 hash map** (dictionary in python) will be used, 1 for storing the corresponding value number to the variable, and 1 for storing the textual string like `"2 - 3"`. We also need a local variable to keep track of the currently assigned value number. 

### Dealing with an abstract syntax tree
Details on dealing with ast can be found [here](https://github.com/usagitoneko97/python-ast/tree/master/A2.ReversingAst)

There is 3 ast node that is important for this assignment.

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
            # It is in, replaces the binop with a single variable
            construct Name Node with id = variable corresponds to the value number
            # replaced the node
            assignNode.value = nameNode
    
    # Always assign the new value number on the lhs of assign class
    Add assignNode.targets[0].id to valueDict
    currentVal += 1
    return asTree
```

The full python source code can be found [here](https://github.com/usagitoneko97/python-ast/blob/master/A3.LVN/lvn.py)

## Extending LVN

**Note**: Features in this section here is still not implemented in `lvn.py`
### Commutative operations
Operation such as `x + y` and `y + x` may produce different key *eg. "0 + 1" or "1 + 0" even though they both meant the same thing. One way to solve this is to sort the operands by ordering their **Value Number**. 

### Algebraic identities
LVN can apply identities to simplify the code. For example. `a * 1` and `a` should have the same value number. 

More example is shown below

![Algebraic identities](https://github.com/usagitoneko97/python-ast/blob/master/A3.LVN/resources/algebraicId.png)


## References
- Torczon, L. and Cooper, M. ed., (2012). Ch8 - Introduction to optimization. In: Engineering a compiler, 2nd ed. Texas: Elsevier, Inc, pp.420-428.
