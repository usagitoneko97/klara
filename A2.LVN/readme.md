# Local value numbering
consider the following code
```python
a = b + c
d = a - b
e = b + c
```
The expression `b + c` is redundant in 3rd line of the assignment since `b + c` is already computed at the first assignment and no intervening operation redefines the arguments. The compiler should rewrite this block so `b + c` only have to compute once. 
```python
a = b + c
d = a - d
e = a
```
One of the techniques is Local Value Numbering. 

## The algorithm
Let's consider the example above. In the first operation, the variables on the right hand side will get the value number first, either previously defined, or assigning new value number. 

![lvnFirst](https://github.com/usagitoneko97/python-ast/blob/master/A2.LVN/resources/lvnFirst.svg)

Lvn then construct the textual string **"0 + 1"** as a hash key to perform lookup. It will fail since there is no previous insertion. LVN then creates an entry of **"0 + 1"** and assigns the value to `"a"`. The final step for one expression is create an entry for variable at the left side. *Keep in mind that variable(s) at the left hand side will always be assign a new value number.* That is, lvn create an entry for `"a"` and assign new value number namely `2`. 

Moving on the second expression, lvn will perform the same step as above. 

![lvnSecond](https://github.com/usagitoneko97/python-ast/blob/master/A2.LVN/resources/lvnSecond.svg)

Because of textual string `"2 - 3"` is not found in the hash map, it will perform the exact step as above. 

On the third expression, 

![lvnThird](https://github.com/usagitoneko97/python-ast/blob/master/A2.LVN/resources/lvnThird.svg)

Now because of string `"0 + 1"` is found in the hash, lvn will replace the expression on the right with result of `"0 + 1"`, namely a.

![lvnReplaced](https://github.com/usagitoneko97/python-ast/blob/master/A2.LVN/resources/lvnReplaced.svg)
