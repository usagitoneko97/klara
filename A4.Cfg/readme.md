# Global Value Numbering

In the previous topics, Local Value Numbering is only handling local scope of the program. To apply Value Numbering to the global scope, multiple steps and algorithm need to be done. The example below shows the problems faced during Value Numbering Operation. 

```python
a = 4
if z < 3:
    b = 4
else:
    b = 5
f = b
```



Control Flow Graph is used to represent the all the path that might be traversed through a program during its execution. I.e., 


will produce control flow graph as below. 

![cfg1]()

Converting a simple block is relatively simpleTo convert the graph to SSA form, some problems may occurs. For example, the 
