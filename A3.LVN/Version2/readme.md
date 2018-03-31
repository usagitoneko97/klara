# 1 Python implementation version 2
The purpose of the version 2 is to improve the readability of the code as well as the newly added ssa implementation. 

## 1.1 Using the Class
Before lvn optimization start, a full list of the ssa need to be obtained. 
```python
as_tree = ast.parse("some_str = x1 + x2")
ssa_code = SsaCode(as_tree)
```
To use lvn optimization, 
```python
lvn_handler = Lvn()
ssa_optimized = lvn_handler.optimize(ssa_code)
print(ssa_optimized)
```

The implementation of the `optimize` function is simply, 
```python
def optimize(self, ssa_code):
    for ssa in ssa_code:
        # Enumerate the expression or variable at the right hand side
        self.lvn_dict.enumerate_rhs(ssa)
        # get simple expr class that contain the information like the value
        # number for left, right operand and operator. 
        simple_expr = self.lvn_dict.get_simple_expr(ssa)
        # enumerate the variable at the left hand side
        self.lvn_dict.enumerate_lhs(ssa)
        # add simple expression to the dictionary
        self.lvn_dict.add_simple_expr(simple_expr)

    ssa_optimized_code = self.lvn_code_to_ssa_code()
    return ssa_optimized_code
```
A few example on showing how lvn can optimize a code. 
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
And console will be showing, 
```python
>>> a_2 = x + y
>>> b = a_2
>>> a = 17
>>> c = a_2
```

## 1.2 Details of the Implementation
The same concept on previous page in the [algorithm](https://github.com/usagitoneko97/python-ast/tree/master/A3.LVN#113-algorithm-in-details) section will reapplied here. A few more data structure need to be added on top of Version 1 to implement a ssa. Apart from the 2 dictionaries used before which is one for storing the value number of variables, and another is to store the simple expression, additional data structures like list and tuple will be used to fully implement the ssa. 

### 1.2.1 Lvn Code Tuples List
The tuples, namely `lvn_code_tuples_list` is to provide the representation of the ssa source code in a form of value number (All operands and target are numbers). One of the problem that you will quickly realise is that after conversion, the variable and constant will be converted to numbers, and that may cause confusion. One way to solve this is to **append a flag** at the end of the tuple, to annotate that either left or right operand is constant. **Note** that there will be no cases where left and right are both constant since it will be folded during the conversion from ast to ssa.


- operand_type = 0   --> no constant
- operand_type = 1   --> left is constant
- operand_type = 2   --> right is constant

To incoporate the ssa into our dictionary, whenever a variable that going to replaced by a newer entry, the old entry will not be removed, instead, an abitary number, the value number of that key will be append to the old key. I.e., 

a = 33

| key | value |
|:---:|:---:  |
| 'a' |   0   |

a = 44

| key | value |
|:---:|:---:  |
| 'a_0'|   0   |
| 'a' |   1   |

The following example will demonstrate how the dictionary and the tuples list get inserted

```python
x = a + b
y = a + 33
z = 44 + x
x = 55
h = a + b
``` 
**Value Number Dictionary**

| key | value | 
| :--:| :---: |
| 'a' |  0    |
| 'b' |  1    |
| 'x_2' |  2    |
| 'y' |  3    |
| 'z' |  4    |
| 'x' |  5 |
| 'h' | 6 |

---
Because of the key in the simple expression involves only numbers, there's a need to know whether the number is correspond to variable or just a constant. The operand_type variable previously will be append to the value to form a list. 

**Simple Expression Dictionary**

| Key     | Value (Value Number, operand_type) |
| :--:    | :---: |
| "0 + 1" |   2, 0|
| "0 + 33" |  3, 2|
| "44 + 2" | 3, 1  |
| "55"   |    5, 1|

**lvn_code_tuples_list**

The first 4 statements will be inserted into the tuples below without substitution. But on the last statement, because of `a + b` or simple expression `0 + 1` is existed in Simple Expression Dictionary, it will substitute `a + b`with `x`, or `0 + 1` with `2` only if the want-to-add simple expression's **operand_type** flag is the same with the entry of Simple Expression dictionary. This is to prevent `a + 1` get substitute with `a + b` when `b` has a value number 1. 

| target | left | operator | right | operand_type |
| :----: | :---:|  :---:   | :---: |  :-----:    |
| 2      |  0   |   '+'    |  1    |    0        |
| 3      |  0   |   '+'    |  33   |    2        |
| 4      |  44  |   '+'    |  3    |    2        |
| 5      |  55  |   None   |  None |    1        |
| 6      |  2   |   None   |  None |    0        |

---

### 1.2.2 Value Number to Variable List
To convert the tuples above back to ssa form, a list is implemented to find out the which variables is correspond to which value number. It can be in a list since all variable will have an unique value number. Whenever a variable is being reassigned or a value number is distributed, it will append at the back at the list. When the variable that are reassigned is already exist in the list, it will append some arbitrary value at the back of the old variable to differentiate between the old and new variable. Using the example above,the list will be, 

    ['a', 'b', 'x', 'y', 'z', 'x_5', 'h']
      |    |    |    |    |     |     |
      0    1    2    3    4     5     6
 
The final step is to convert the **lvn_code_tuples_list** to the ssa_code list. It will convert all the value number to the variable that represent by the list above. For example, the first list of the tuples_list will generate `2 = 0 + 1` and map to `x = a + b`. 

