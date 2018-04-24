# Static Single Assignment

## Introduction to SSA
Static single assignment (SSA) had been discussed previously on [problems when redefining occurs](https://github.com/usagitoneko97/python-ast/tree/master/A3.LVN#114-details-and-solution-for-problems-when-redefining-occurs). SSA helped to solve that particular problem. To recall, to solve the problem, the code had transformed to ssa form.

```python
a = x + y                       
b = x + y            
a = 17               
c = x + y 
```
will transform to:
```python
a_0 = x_0 + y_0                       
b_0 = x_0 + y_0            
a_1 = 17               
c_0 = x_0 + y_0 
```
Transforming the code above to SSA is primarily a simple matter of replacing the target of each assignment with a new variable and with a new version. The code above can be group into a block, namely `Basic Block`. Basic block simply means a straight-line code sequence with no branches except the entry and the exit. 

Now consider the code below:

```python
a = x + y                       
if b < 3:
    x = 0
else:
    x = 1
b = x + y
```

The code above will generate multiple basic blocks, since it has a conditional statement. The basic blocks will then linked between themselves, and form a network of basic blocks, name **Control Flow Graph (CFG)**. 

![cfg_ssa_intro](https://github.com/usagitoneko97/python-ast/blob/master/A4.Cfg/resources/cfg_ssa_intro.svg)

To transform the entire CFG into SSA form, one problem will occur. 

```python
a_0 = x_0 + y_0                       
if b_0 < 3:
    x_1 = 0
else:
    x_2 = 1
b_0 = x_? + y_0
```

At the last statement of the code, the use of x could be refer to either `x_1` or `x_2` depending on the execution to fall into one of the 2 blocks. To resolve this, a special statement is inserted before the last statement, called a **Φ (Phi) function**. This statement will generate a new definition of x called x_3 by "choosing" either x_1 or x_2. 

```python
a_0 = x_0 + y_0                       
if b_0 < 3:
    x_1 = 0
else:
    x_2 = 1
x_3 = Φ(x_1, x_2)
b_0 = x_3 + y_0
```

![cfg_ssa_intro_after_ssa](https://github.com/usagitoneko97/python-ast/blob/master/A4.Cfg/resources/cfg_ssa_intro_after_ssa.svg)

## Minimal SSA 

There are many ways to insert phi function. The easiest way of inserting phi function is to insert it at start of every single basic block. But that could be result in excess amount of unnecessaries phi function. One can argue that phi function can be inserted at every blocks that have joint points (multiple parents), but consider CFG below: 

![cfg_ssa_intro](https://github.com/usagitoneko97/python-ast/blob/master/A4.Cfg/resources/cfg_ssa_intro.svg)

Phi function for variable `y` should not be insert at `B4` since `B2` and `B3` had not declare variable `y`. But phi function of `x` had to be insert just before `B4` since it has been declared in both of the blocks `B2` and `B3`. 

![cfg_ssa_intro_after_ssa](https://github.com/usagitoneko97/python-ast/blob/master/A4.Cfg/resources/cfg_ssa_intro_after_ssa.svg)

Minimal SSA basically means the SSA form that contains the minimum phi function. To complete the job of minimal SSA, they are a few of the representation and algorithm that are required. Section here will explain all the algorithm that are required to built compute a minimal SSA. 

### Terminology

- **Dominate** - A node u is said to *dominate* a node w w.r.t
source vertex S if all the paths from S to w in the graph must pass through
node u.

- **Immediate Dominator** - A node u is said to be an *immediate dominator*
of a node w (denoted as idom(w)) if u dominates w and every other
dominator of w dominates u.

- **Strictly Dominates** - A node `d` is said to *strictly dominates* node `n` if d dominates `n` and `d` does not equal `n`

- **dominance frontier** - The *dominance frontier* of a node `d` is the set of all nodes `n` such that d dominates an immediate predecessor of `n`, but `d` does not strictly dominate `n`.

- **dominator tree** - A *dominator tree* is a tree where each node's children are those nodes it immediately dominates. Because the immediate dominator is unique, it is a tree. The start node is the root of the tree.


### Dominance

#### Introduction
As stated in terminology section above, A node u is said to *dominate* a node w w.r.t source vertex S if all the paths from S to w in the graph must pass through node u. Take for example the graph below, Assume the source is `B1`:

![cfg_ssa_intro](https://github.com/usagitoneko97/python-ast/blob/master/A4.Cfg/resources/cfg_ssa_intro.svg)

First, we will find a list of dominated nodes by `B1`. On `B2`, it's clear that the only path to `B2` passes through `B1`, so we can safely say that `B1` dominates `B2`. The same goes to `B3`. On `B4` even though it has 2 path going to `B4`, 2 of the path has to pass through `B1`, so `B1` dominates `B3`. 

To find the dominated nodes list of `B2`, we look for the children of `B2`. To reach `B4`, the programs can take the path on the right side and not pass through `B2`, so `B1` does not **dominates** `B2`. 

The complete list of dominace relationship is shown below:

**B1** : [**B2**, **B3**, **B4**]
**B2** : []
**B3** : []
**B4** : []

#### Algorithm
They are a few ways to calculate the dominance relationship between nodes. One of the easiest way is, for each node `w`, remove the node from the graph and perform a DFS from source node and all the nodes that are not visited by DFS is the nodes that dominated by `w`. 


### Dominator Tree

Given a node n in a flow graph, the set of nodes that strictly dominate n is given by (Dom(n) − n). The node in that set that is closest to n is called n’s **Immediate Dominator(IDOM)**. To simplify the relationship of IDOM and DOM, a dominator tree is built. If `m` is `IDOM(n)`, then the dominator tree has an edge from `m` to `n`. The dominator tree for example in section above is shown below: 

![dominance tree](https://github.com/usagitoneko97/python-ast/blob/master/A4.Cfg/resources/dominance_Tree.svg)


### Dominance Frontier

In a simplified manner of explanation, the dominance frontier of a node `n` can be view as, from `n`'s point of view, going through his child, DF node is the first node that `n` doesn't *strictly dominates*. For example, consider following CFG. 

![DF_example](https://github.com/usagitoneko97/python-ast/blob/master/A4.Cfg/resources/DF_example.svg)

Assume that DF of `B5` need to be found, it will iterate thorough both of the child, `B6` and `B8`. Since `B5` dominates both of them, they are not dominance frontier of `B5`. Then it will move on to `B7`, and `B5` still dominates `B7`. On block `B3` however, `B5` does not strictly dominates `B3` hence `B3` is the dominance frontier of `B5`. 

Pseudocode for calculating DF is provided below: 

```
for each node b
    if the number of immediate predecessors of b ≥ 2
        for each p in immediate predecessors of b
            runner := p
            while runner ≠ idom(b)
                add b to runner’s dominance frontier set
                runner := idom(runner)
```

### Placing φ-Functions