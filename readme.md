## Interesting python ast data flow analysis topics and implementation.
This repository explore how one can extract information out of the python's ast. 
To statically analyze the python data flow information, there are several intermediate representation(IR) that provide facilities that are easier to work with during an analysis, without re-inventing the wheel of having to construct custom data flow analysis algorithm on the ast itself.

The IR cover in this repo including *Control flow graph(CFG)* and *Static single assignment(SSA)*. There are details explanation on each topics with implementation provided as a reference.

After all IR has been built, any analysis can then be carried out on the IR. Examples of analysis that can be carried out in CFG+SSA is dead code analysis, use-def/def-use chain and value inference.

`cfg_and_ssa` folder will explain in details about the mentioned IRs, and `lvn_optimization` will further explore interesting way to optimize a python expression.

## References
Below is a list of references that are used in the writing.

- Torczon, L. and Cooper, M. ed., (2012). Ch9 - Data-Flow Analysis. In: Engineering a compiler, 2nd ed. Texas: Elsevier, Inc, pp.495-519.
- Torczon, L. and Cooper, M. ed., (2012). Ch8 - Introduction to optimization. In: Engineering a compiler, 2nd ed. Texas: Elsevier, Inc, pp.445-457.
- Braun, M., Buchwald, S., Hack, S., Leißa, R., Mallon, C., & Zwinkau, A. (2013). Simple and efficient construction of static single assignment form. Lecture Notes in Computer Science (Including Subseries Lecture Notes in Artificial Intelligence and Lecture Notes in Bioinformatics), 7791 LNCS(March), 102–122. https://doi.org/10.1007/978-3-642-37051-9_6
- Cytron, R., Ferrante, J., Rosen, B. K., Wegman, M. N., & Zadeck, F. K. (1991). Efficiently computing static single assignment form and the control dependence graph. ACM Transactions on Programming Languages and Systems, 13(4), 451–490. https://doi.org/10.1145/115372.115320


