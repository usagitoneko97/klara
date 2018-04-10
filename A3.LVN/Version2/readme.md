# 1 Python Implementation version 2
This version improves on the earlier one by including SSA to solve **variable-redefinition** problem. Also, the code was revamped to be expressive and modular to improve readability.

Now the `optimize` function is short and expressive without implementation details exposed:
```python
 def optimize(self, ssa_code):
    for ssa in ssa_code:
        self.lvn_dict.variable_dict.enumerate(ssa)
        lvn_stmt = self.lvn_dict.get_lvn_stmt(ssa)
        if lvn_stmt.is_simple_assignment():
            # try to replace the left operand
            lvn_stmt.left = self.lvn_dict.simple_assign_dict.find_substitute(lvn_stmt.left)
            self.lvn_dict.simple_assign_dict.update_simp_assgn(lvn_stmt.target, lvn_stmt.left)

        else:
            lvn_stmt.left = self.lvn_dict.simple_assign_dict.find_substitute(lvn_stmt.left)
            lvn_stmt.right = self.lvn_dict.simple_assign_dict.find_substitute(lvn_stmt.right)
            lvn_stmt = self.lvn_dict.find_substitute(lvn_stmt)
            if not lvn_stmt.is_simple_assignment():
                self.lvn_dict.add_expr(lvn_stmt.get_expr(), lvn_stmt.target)
            else:
                # it's simple expr, add into simple_assign_dict
                self.lvn_dict.simple_assign_dict.update_simp_assgn(lvn_stmt.target, lvn_stmt.left)

        self.lvn_dict.lvn_code_tuples_list.append_lvn_stmt(lvn_stmt)

    ssa_optimized_code = self.lvn_code_to_ssa_code()
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
>>> a_0 = x_0 + y_0
>>> b_0 = a_0
>>> a_1 = 17
>>> c_0 = a_0
```
Note: `a_0` can be viewed as *temporary* variable of `a`, since the latter is reassigned with a constant value of 17 at the 3rd statement. The temporary variable is important because it is used to optimize assignment of `c` at the last statement.

## 1.2 Details of the Implementation
The same concept on the previous page in the [algorithm](https://github.com/usagitoneko97/python-ast/tree/master/A3.LVN#113-algorithm-in-details) section is reapplied here. Apart from the 2 dictionaries used before, one for storing the value numbers of variables and the other for the algebraic expression, additional data structures like list and tuple is added to allow incorporation of the SSA. 

### 1.2.1 Terminology

**Value Number**

A unique number assigned to a variable

**Simple assignment** 

Means only either one variable or one constant value exists on the RHS in an equation. i.e.,
```
a = b
a = 3123
```
**Lvn Statement**

It's a statement but in Value Number form. I.e., 
```
3 = 0 + 1
4 = 2
```

**Expression**

It only contains operands and an operator. Because of all the SSA is in TAC form, it can only have at most 2 operands and 1 operator. I.e.,
```
a + d
34 + c
- e
```

### 1.2.2 Transformation from AST to SSA
Before any analysis can be done, SSA needs to form from the AST. For example,

    a = b + c 
    
will transform into 

    a_0 = b_0 + c_0

A dictionary needs to be implemented to record the version of all the variables. From the example, the dictionary is as follow:

| key(variable) | Value(version number)|
|  :----:       |    :-------:         |
|   'a'         |         0            |
|   'b'         |         0            |
|   'c'         |         0            |

Assume we have the second statement as follow:

    a = 33

This transform into 

    a_1 = 33

And result in the dictionary as follow:

| key(variable) | Value(version number)|
|  :----:       |    :-------:         |
|   'a'         |         1 (updated)  |
|   'b'         |         0            |
|   'c'         |         0            |

To fully make use of object-oriented design, a class name `SsaVariable` will be created to store all the operands or target of the assignment. SsaVariable will have 2 attributes

- **var** - the variable name. I.e., 'a', '3'
- **version_number** - the version of the variable, will not exist if the var is a number. 

### 1.2.3 Enumerating Variables
To enumerate a variable, a unique **Value-Number** is assigned to the variable. The operands will get the value-number first, then followed by the target. For example,
```python
a_0 = b_0 + c_0
```
will insert 3 entries into the dictionary. 

| Name (key)| LVN (value)|
| :--:| :---: |
| 'b_0' |  0    |
| 'c_0' |  1    |
| 'a_0' |  2    |

There's a need also to find the particular variable using a version number. 
A list can be implemented since each variable has a unique value number. Whenever a variable is being reassigned or a value number is distributed, it will append at the back of the list.

    ['b_0', 'c_0', 'a_0']
       |      |      |   
       0      1      2   

### 1.2.4 LVN Statement
What differs LVN statement from the ordinary statement is that the target and both the operands is in Value-Number form. Using the same example and assumes the variables had been enumerated and the dictionary is as shown above,  

```python
a_0 = b_0 + c_0
```

will transform into:

```python
2 = 0 + 1
```

LVN statement will ease our analysis later on. 

### 1.2.5 Storing Simple Assignment and It's Uses
The details can be found [here](https://github.com/usagitoneko97/python-ast/tree/master/A3.LVN#115-details-and-solution-for-indirect-substitution). In the real implementation, however, all the operands will substitute accordingly based on Simple Assignment Dictionary. The example below will demonstrate the idea. 

```python
z = a + y
b = a
c = b       # c = a
d = c + y   # d = a + y
```

There's no need to search the replacement for 'c + y'. Instead, 'c' will be substituted with 'a' every time. So to conclude, **all the operands should substitute accordingly everytime**.   

### 1.2.6 Expression substitution and code generation
This [section](https://github.com/usagitoneko97/python-ast/tree/master/A3.LVN#113-algorithm-in-details) discuss on the substitution of the statement with appropriate expression. The substituted statement will then add into a list of tuple.  `lvn_code_tuples_list` is the SSA code represented in the form of value number. It contains full information about how the code looks like. 

For example, 

```python
z = a + y
b = a
c = b       # c = a
d = c + y   # d = a + y  --> d = z
```

After performing all the steps explained above from section **1.2.1** onwards, the list of LvnExpression will look like:
```
2 = 0 + 1 # z = a + y
3 = 0     # b = a
4 = 0     # c = a 
5 = 2     # d = z   ---> substituted
``` 

Converting this back to SSA is fairly simple. It will look up the variable associated with this value number by the list that built-in [section1.2.3](https://github.com/usagitoneko97/python-ast/tree/master/A3.LVN/Version2#123-enumerating-variables). 

Result:
```python
z_0 = a_0 + y_0
b_0 = a_0
c_0 = a_0 
d_0 = z_0
``` 

### 1.2.7 Optimizing Algebraic Identities
To recall, Algebraic Identities had been discussed [here](https://github.com/usagitoneko97/python-ast/tree/master/A3.LVN#132-algebraic-identities). To simplify the implementation, we can break the algebraic identities by looking at the operator. Take, for example, the `'+'` operator will only have to take care of when one of the operands is 0. I.e.,
```python
x = a + 0
x = 0 + a
```
This separation of concerns greatly helps to reduce the complexity of the implementation. 

A class name `AlgIdent` is built specifically to handle all the operations related to algebraic identities. To separate them by the operator, the function needs to be declared that specifically handle that operator. For example, the function below will try to simplify the expression related to `+` operator. 

```python
def alg_ident_add(self, left, right):
    if left == 0:
        return right, None, None
    elif right == 0:
        return left, None, None
    else:
        return left, 'Add', right
    pass
```

To relate the function to the operator, a dictionary will be implemented.

| operator (key)| op_func (value)|
| :--:| :---: |
| 'Add' |  self.alg_ident_add|
| 'Sub' |  self.alg_ident_Sub|
| 'Mult' |  self.alg_ident_mult|
|...|...|

After everything is in place, the optimize function is simply, 
```python
def optimize_alg_identities(self, left, op, right):
    if op is None:
        return left, op, right
    else:
        # find respective func through this dict
        op_func = self.find_operands_func(op)
        if op_func is not None:
            left, op, right = op_func(left.get_var(), right.get_var())
            return left, op, right
        return left, op, right
```

**Note**: the left, right parameter on function above is in SsaVariable type. recall [here](https://github.com/usagitoneko97/python-ast/tree/master/A3.LVN/Version2#122-transformation-from-ast-to-ssa). 

### 1.2.8 Constant Folding
Constant folding is required when both of the operands is constant. See [Constant Propagation](). For example, assume the following code need to be folded. 
```python
x = 33 + 44
```
The whole idea is to built the expression string `33 + 44` and use the python built-in function `eval` to calculate the value. 

## 1.3 Example
The following is a code example to demonstrate the algorithm:

**input ast**
```python
x = a + b
y = a + 33
z = 44 + x
x = 55
h = a + b
```

By performing all the steps in 1.2 will result in:

**SSA Code**
```python
x_0 = a_0 + b_0
y_0 = a_0 + 33
z_0 = 44 + x_0
x_1 = 55
h_0 = a_0 + b_0
``` 

**Value Number Dictionary**

| Name (key)| LVN (value)|
| :--:| :---: |
| 'a_0' |  0    |
| 'b_0' |  1    |
| 'x_0' |  2    |
| 'y_0' |  3    |
| 'z_0' |  4    |
| 'x_1' |  5 |
| 'h_0' | 6 |

**val_num_var_list**
```
   ['a_0', 'b_0', 'x_0', 'y_0', 'z_0', 'x_1', 'h_0']
      |      |      |      |      |      |      |
      0      1      2      3      4      5      6
```

**Algebraic Expression Dictionary**

| Key     | Value (value number) |
| :--:    | :---: |
| "0 + 1" |   2|
| "0 + 33" |  3|
| "44 + 2" | 3  |
| "55"   |    5|

The first 4 statements are inserted into the tuples below without substitution. But on the last statement, because of `a + b` or the algebraic expression `0 + 1` already existed in the Algebraic Expression Dictionary, it substitutes `a + b` with `x`, or `0 + 1` with `2`. 

**LVN Code (lvn_code_tuples_list)**

| target* | left | operator | right |
| :----: | :---:|  :---:   | :---: | 
| 2      |  0   |   '+'    |  1    | 
| 3      |  0   |   '+'    |  33   | 
| 4      |  44  |   '+'    |  3    | 
| 5      |  55  |   None   |  None | 
| 6      |  2   |   None   |  None | 

* *target* means LHS variable of the assignment expression. 

With this LVN Code, it can convert back to SSA easily by referring to **val_num_var_list**. 

```python
x_0 = a_0 + b_0
y_0 = a_0 + 33
z_0 = 44 + x_0
x_1 = 55
h_0 = x_0
``` 