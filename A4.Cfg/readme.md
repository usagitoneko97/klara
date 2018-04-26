# Static Single Assignment

## Basic blocks

### Introduction to Control Flow Graph (CFG) and Basic Blocks
Basic block simply means a straight-line code sequence with no branches except the entry and the exit. 

E.g., 
```python
a = x + y                       
b = x + y            
a = 17               
c = x + y 
```

The code above can be group into a block, namely `Basic Block`. 

Now take a look at the code below. 

```python
a = x + y                       
if b < 3:
    x = 0
else:
    x = 1
b = x + y
```

The code above will generate multiple basic blocks since it has a branching statement. The basic blocks will then linked between themselves, and form a network of basic blocks, name **Control Flow Graph (CFG)**. 

![cfg_ssa_intro](https://github.com/usagitoneko97/python-ast/blob/master/A4.Cfg/resources/cfg_ssa_intro.svg.png)

### Transforming SSA to CFG

Transforming SSA to CFG (multiple basic blocks) will required a recursive algorithm, since the program could be nested branch statement. For example, 

```python
x = a + b
if x < 2:
    if a < 2:
        a = 2
else:
    a = 3
```

The recursive function will require returning the head basic block and the tail basic block to the caller. The caller can then use the head and tail return to connects both of the blocks. I.e., in *If* statement, the caller will pass the body of If to the recursive function, and will connect itself with the head returned, and connects the tail to the next basic block. At the end of the operation, it will return the head and tail for the list of ast statement. 

## Revisiting SSA
Static single assignment(SSA) had been discussed previously on [problems when redefining occurs](https://github.com/usagitoneko97/python-ast/tree/master/A3.LVN#114-details-and-solution-for-problems-when-redefining-occurs). SSA helped to solve that particular problem. To recall, to solve the problem, the code had transformed to SSA form.

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

And will obtain:

```python
a_0 = x_0 + y_0                       
b_0 = a_0
a_1 = 17               
c_0 = a_0
```

Transforming the code above to SSA is primarily a simple matter of replacing the target of each assignment with a new variable and with a new version.

Now consider the code below:

```python
a = x + y                       
if b < 3:
    x = 0
else:
    x = 1
b = x + y
```

![cfg_ssa_intro](https://github.com/usagitoneko97/python-ast/blob/master/A4.Cfg/resources/cfg_ssa_intro.svg.png)

To transform a CFG, especially a branching of basic blocks, to SSA form is not as straightforward as above. The code below will demonstrate the problem. 

```python
a_0 = x_0 + y_0                       
if b_0 < 3:
    x_1 = 0
else:
    x_2 = 1
b_0 = x_? + y_0
```

At the last statement of the code, the use of `x` could be referring to either `x_1` or `x_2` depending on the execution to fall into one of the 2 blocks. To resolve this, a special statement is inserted before the last statement, called a **Φ (Phi) function**. This statement will generate a new definition of `x` called `x_3` by "choosing" either `x_1` or `x_2`. 

```python
a_0 = x_0 + y_0                       
if b_0 < 3:
    x_1 = 0
else:
    x_2 = 1
x_3 = Φ(x_1, x_2)
b_0 = x_3 + y_0
```

![cfg_ssa_intro_after_ssa](https://github.com/usagitoneko97/python-ast/blob/master/A4.Cfg/resources/cfg_ssa_intro_after_ssa.svg.png)

## Minimal SSA 

There are many ways to insert phi function. The easiest way of inserting phi function is to insert it at every block that have joint points (multiple parents). But that could result in an excess amount of unnecessaries phi function. Consider the CFG below: 

![cfg_ssa_intro](https://github.com/usagitoneko97/python-ast/blob/master/A4.Cfg/resources/cfg_ssa_intro.svg.png)

 Phi function of `x` had to be inserted just before `B4` since it has been declared in both of the blocks `B2` and `B3`. But phi function for variable `y` should not be inserted at `B4` since `B2` and `B3` had not declared variable `y`.

![cfg_ssa_intro_after_ssa](https://github.com/usagitoneko97/python-ast/blob/master/A4.Cfg/resources/cfg_ssa_intro_after_ssa.svg.png)

Minimal SSA basically means the SSA form that contains the minimum phi function. To complete the job of minimal SSA, they are a few of additional tree structures and algorithm that are required. The section here will explain all the algorithm that is required to compute a minimal SSA. 

### Terminology

- **Dominate** - A node `u` is said to *dominate* a node w w.r.t
source vertex `s` if all the paths from `s` to `w` in the graph must pass through
node u.

- **Immediate Dominator** - A node `u` is said to be an *immediate dominator*
of a node `w` (denoted as `idom(w)`) if `u` dominates `w` and every other
dominator of `w` dominates `u`.

- **Strictly Dominates** - A node `d` is said to *strictly dominates* node `n` if `d` dominates `n` and `d` does not equal `n`

- **dominance frontier** - The *dominance frontier* of a node `d` is the set of all nodes `n` such that d dominates an immediate predecessor of `n`, but `d` does not strictly dominate `n`.

- **dominator tree** - A *dominator tree* is a tree where each node's children are those nodes it immediately dominates. Because the immediate dominator is unique, it is a tree. The start node is the root of the tree.


### Dominance

#### Introduction
As stated in terminology section above, A node `u` is said to *dominate* a node `w` w.r.t source vertex `s` if all the paths from `s` to `w` in the graph must pass through node `u`. Take for example the graph below, Assume the source is `B1`:

![cfg_ssa_intro](https://github.com/usagitoneko97/python-ast/blob/master/A4.Cfg/resources/cfg_ssa_intro.svg.png)

First, we will find a list of dominated nodes by `B1`. On `B2`, it's clear that the only path to `B2` passes through `B1`, so we can safely say that `B1` dominates `B2`. The same goes for `B3`. On `B4` even though it has 2 paths going to `B4`, 2 of the path has to pass through `B1`, so `B1` dominates `B4`. 

To find the dominated nodes list of `B2`, we look for the children of `B2`. To reach `B4`, the programs can take the path on the right side and not pass through `B2`, so `B2` does not **dominates** `B4`. 

The complete list of dominace relationship is shown below:

**B1** : [**B2**, **B3**, **B4**]

**B2** : []

**B3** : []

**B4** : []

The dominator tree can then be built from this list. Dominator tree will be discussed in detail on the Dominator Tree section below. 

![dominance tree](https://github.com/usagitoneko97/python-ast/blob/master/A4.Cfg/resources/dominance_Tree.svg.png)

#### Algorithm

They are a few ways to calculate the dominance relationship between nodes. One of the easiest ways is, for each node `w`, remove the node from the graph and perform a [DFS](https://en.wikipedia.org/wiki/Depth-first_search) from source node and all the nodes that are not visited by DFS are the nodes that dominated by `w`. 

### Dominator Tree

#### Introduction
Given a node n in a flow graph, the set of nodes that strictly dominate `n` is given by `(Dom(n) − n)`. The node in that set that is closest to n is called n’s **Immediate Dominator(IDOM)**. To simplify the relationship of IDOM and DOM, a dominator tree is built. If `m` is `IDOM(n)`, then the dominator tree has an edge from `m` to `n`. The dominator tree for example in the section above is shown below: 


![dominance tree](https://github.com/usagitoneko97/python-ast/blob/master/A4.Cfg/resources/dominance_Tree.svg.png)
#### Algorithm

The algorithm for constructing the dominance tree is fairly simple. Consider a slightly complex dominance relationship of a tree. 

![dominator_tree_example](https://github.com/usagitoneko97/python-ast/blob/master/A4.Cfg/resources/dominator_tree_example.svg.png)

And the dominance relationship between nodes is shown below:

**B0** : [**B1**, **B2**, **B3**]

**B1** : [**B2**, **B3**]

**B2** : []

**B3** : []

To build the tree, first go down to the bottom of the tree and start to build the dominator tree from bottom to the top. For every node `u` starting from the bottom, `u` will be added to the dominator tree, and will attach node that `u` dominates and doesn't have a parent. This will result in **B0** does not have **B2** and **B3** as it's child.

The dominator tree:

![dominator_tree_example_result](https://github.com/usagitoneko97/python-ast/blob/master/A4.Cfg/resources/dominator_tree_example_result.svg.png)  

### Dominance Frontier

In a simplified manner of explanation, the dominance frontier of a node `n` can be view as, from `n`'s point of view, going through his child, DF node is the first node that `n` doesn't *strictly dominates*. For example, consider following CFG. 

![DF_example](https://github.com/usagitoneko97/python-ast/blob/master/A4.Cfg/resources/DF_example.svg)

Assume that DF of `B5` needs to be found, it will iterate through both of the child, `B6` and `B8`. Since `B5` dominates both of them, they are not dominance frontier of `B5`. Then it will move on to `B7`, and `B5` still dominates `B7`. On block `B3` however, `B5` does not strictly dominates `B3` hence `B3` is the dominance frontier of `B5`. 

Pseudocode for calculating DF is provided below: 

```
for each node b
    if the number of immediate predecessors of b ≥ 2
        for each p in immediate predecessors of b
            runner := p.
            while runner ≠ idom(b)
                add b to runner’s dominance frontier set
                runner := idom(runner)
```

### Placing φ-Functions
With dominance frontier, the phi function can be now place strategically. But in order to further minimize the number of phi function, liva variable analysis can be use to find out whether the phi function for that particular variable is needed or not. 