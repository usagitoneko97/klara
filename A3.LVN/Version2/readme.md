# 1 Python Implementation version 2
This version improves on the ealier one by including SSA to solve **variable-redefinition** problem. Also, the code was revamped to be expressive and modular to improve readability.

Now the `optimize` function is short and expressive without implementation details exposed:
```python
def optimize(self, ssa_code):
    for ssa in ssa_code:
        # Enumerate the RHS variable
        self.lvn_dict.enumerate_rhs(ssa)
        # Get algebraic expr class that contains the information like the values
        # number for left and right operands, and operator. 
        algebraic_expr = self.lvn_dict.get_algebraic_expr(ssa)
        # Enumerate the RHS variables
        self.lvn_dict.enumerate_lhs(ssa)
        # add algebraic expression to the dictionary
        self.lvn_dict.add_algebraic_expr(algebraic_expr)

    ssa_optimized_code = self.lvn_to_ssa()
    return ssa_optimized_code
```

## 1.1 Using the Class
Before applying LVN optimization, the code in AST form is transformed into SSA form: 
```python
as_tree = ast.parse("some_str = x1 + x2")
ssa_code = SsaCode(as_tree)
```
then the LVN optimization is applied: 
```python
lvn_handler = Lvn()
ssa_optimized = lvn_handler.optimize(ssa_code)
print(ssa_optimized)
```

The following shows an example on how to use the code. 
```python
as_tree = ast.parse(ms("""\
    a = x + y
    b = x + y
    a = 17
    c = x + y"""))
lvn_test = Lvn()
ssa_code = SsaCode(as_tree)
ssa_code = lvn_test.optimize(ssa_code)

print(ssa_code)
```
Running the program will dump the following output: 
```python
>>> a_2 = x + y
>>> b = a_2
>>> a = 17
>>> c = a_2
```
Note: `a_2` can be viewed as *temporary* variable of `a`, since the latter is reassigned with a constant value of 17 at the 3rd statement. The temporary variable is important because it is used to optimize assignment of `c` at the last statement.

## 1.2 Details of the Implementation
The same concept on the previous page in the [algorithm](https://github.com/usagitoneko97/python-ast/tree/master/A3.LVN#113-algorithm-in-details) section is reapplied here. Apart from the 2 dictionaries used before, one for storing the value numbers of variables and the other for the algebraic expression, additional data structures like list and tuple is added to allow incorporation of the SSA. 

### 1.2.1 LVN Code Tuples List
The tuples, namely `lvn_code_tuples_list`, is the SSA code represented in the form of value number. All operands and target are numbers, which means a variable cannot be distinguished from a constant value. The last element, known as the `operand_type`, in the tuple is the flag to indicate the type of the operands.   

- operand_type = 0   --> both operands are variable
- operand_type = 1   --> left operand is constant
- operand_type = 2   --> right operand is constant
- operand_type = 3   --> both operands are constant

To implement the SSA, whenever a variable is redefined the old variable is not removed, but is renamed instead. This is done by appending a unique number to the name. The choice of number implemented in the code is the LVN value assigned to that old variable, since it the simplest way and the number is unique. For example, 

```python
a = 33
a = 44
a = 55
```

When `a = 33` is processed, the name of the variable and its LVN is:

| Name | LVN |
|:---:|:---:  |
| 'a' |   0   |

When `a = 44` is processed, then

| Name | LVN |
|:---:|:---:  |
| 'a_0'|   0   |
| 'a' |   1   |

Finally, when `a = 55` is processed, then

| Name | LVN |
|:---:|:---:  |
| 'a_0'|   0  |
| 'a_1' |   1  |
| 'a' |   2  |

### 1.2.2 Example
The following is a code example to demonstrate the algorithm:

```python
x = a + b
y = a + 33
z = 44 + x
x = 55
h = a + b
``` 

The result is:

**Value Number Dictionary**

| Name (key)| LVN (value)|
| :--:| :---: |
| 'a' |  0    |
| 'b' |  1    |
| 'x_2' |  2    |
| 'y' |  3    |
| 'z' |  4    |
| 'x' |  5 |
| 'h' | 6 |

Recall that the key in the algebraic expression involves only number, so there is a need to know whether the number corresponds to a variable or just a constant value. The `operand_type` is added to the dictionary `Value` to annotate the operands' type: 

**Algebraic Expression Dictionary**

| Key     | Value (value number, operand_type) |
| :--:    | :---: |
| "0 + 1" |   2, 0|
| "0 + 33" |  3, 2|
| "44 + 2" | 3, 1  |
| "55"   |    5, 1|

The first 4 statements is inserted into the tuples below without substitution. But on the last statement, because of `a + b` or the algebraic expression `0 + 1` already existed in the Algebraic Expression Dictionary, it substitutes `a + b` with `x`, or `0 + 1` with `2` only if the want-to-add simple expression's **operand_type** flag is the same with the entry of Algebraic Expression dictionary. This is to prevent `a + 1` get substitute with `a + b` when `b` has a value number 1. 

**LVN Code (lvn_code_tuples_list)**

| target* | left | operator | right | operand_type |
| :----: | :---:|  :---:   | :---: |  :-----:    |
| 2      |  0   |   '+'    |  1    |    0 (both are variables) |
| 3      |  0   |   '+'    |  33   |    2 (right is constant)  |
| 4      |  44  |   '+'    |  3    |    1 (left is constant)  |
| 5      |  55  |   None   |  None |    1 (left is constant)   |
| 6      |  2   |   None   |  None |    0 (both are variables) |

* *target* means LHS variable of the assignment expression. 


---

### 1.2.2 Converting Back To SSA
To convert the tuples above back to SSA form, a list is implemented to find out which variable correspond to which value number. It can be in a list since each variable has unique value number. Whenever a variable is being reassigned or a value number is distributed, it will append at the back of the list. When the variable that is reassigned/redefined has already existed in the list, it is appended with some unique value of the name of the variable to differentiate old from new. Using the example above, the list will be, 

    ['a', 'b', 'x', 'y', 'z', 'x_5', 'h']
      |    |    |    |    |     |     |
      0    1    2    3    4     5     6
 
The SSA code for the LVN code in the example above is:
```python
x = a + b
y = a + 33
z = 44 + x
x = 55
h = x_2
``` 
