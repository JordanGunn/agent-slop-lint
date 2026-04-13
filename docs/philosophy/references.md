# References

Full bibliography of the research slop's metrics are built on.

## Primary sources (metrics implemented in slop)

- **McCabe, T.J.** (1976). "A Complexity Measure." *IEEE Transactions on
  Software Engineering*, SE-2(4), 308-320.
  → `complexity.cyclomatic`

- **Campbell, G.A.** (2018). "Cognitive Complexity: A new way of measuring
  understandability." SonarSource SA. Technical report.
  → `complexity.cognitive`

- **Chidamber, S.R. & Kemerer, C.F.** (1994). "A Metrics Suite for Object
  Oriented Design." *IEEE Transactions on Software Engineering*, 20(6),
  476-493.
  → `complexity.weighted` (WMC), `class.coupling` (CBO),
  `class.inheritance.depth` (DIT), `class.inheritance.children` (NOC)

- **Martin, R.C.** (1994). "OO Design Quality Metrics: An Analysis of
  Dependencies." *Proceedings of Workshop Pragmatic and Theoretical
  Directions in Object-Oriented Software Metrics*, OOPSLA '94.
  → `packages` (D', I, A)

- **Martin, R.C.** (2002). *Agile Software Development: Principles,
  Patterns, and Practices*. Prentice Hall. Chapter 20.
  → `packages` (expanded treatment)

- **Tornhill, A.** (2015). *Your Code as a Crime Scene: Use Forensic
  Techniques to Arrest Defects, Bottlenecks, and Bad Design in Your
  Programs*. Pragmatic Bookshelf.
  → `hotspots`

- **Tarjan, R.E.** (1972). "Depth-First Search and Linear Graph
  Algorithms." *SIAM Journal on Computing*, 1(2), 146-160.
  → `deps` (cycle detection)

## Secondary sources (cited in rationale)

- **Bainbridge, L.** (1983). "Ironies of Automation." *Automatica*,
  19(6), 775-779.

- **Cunningham, W.** (1992). "The WyCash Portfolio Management System."
  *OOPSLA '92 Experience Report*.

- **Denison, E. et al.** (2024). "Sycophancy to Subterfuge: Investigating
  Reward-Tampering in Language Models." Anthropic.

- **Fowler, M.** (1999). *Refactoring: Improving the Design of Existing
  Code*. Addison-Wesley.

- **Gall, H., Hajek, K., & Jazayeri, M.** (1998). "Detection of Logical
  Coupling Based on Product Release History." *Proceedings of the
  International Conference on Software Maintenance*.

- **Henry, S. & Kafura, D.** (1981). "Software Structure Metrics Based on
  Information Flow." *IEEE Transactions on Software Engineering*,
  SE-7(5), 510-518.

- **Mäntylä, M., Vanhanen, J., & Lassenius, C.** (2003). "A Taxonomy and
  an Initial Empirical Study of Bad Smells in Code." *Proceedings of the
  International Conference on Software Maintenance*.

- **Nagappan, N. & Ball, T.** (2005). "Use of Relative Code Churn Measures
  to Predict System Defect Density." *Proceedings of the 27th
  International Conference on Software Engineering*.

- **Page-Jones, M.** (1996). *What Every Programmer Should Know About
  Object-Oriented Design*. Dorset House.

- **Parasuraman, R. & Riley, V.** (1997). "Humans and Automation: Use,
  Misuse, Disuse, Abuse." *Human Factors*, 39(2), 230-253.

- **Parnas, D.L.** (1994). "Software Aging." *Proceedings of the 16th
  International Conference on Software Engineering*.

- **Sharma, M. et al.** (2023). "Towards Understanding Sycophancy in
  Language Models." Anthropic.

- **Weirich, J.** (2009). "Connascence Examined." Presentation.

## Metrics not yet implemented

- **Halstead, M.** (1977). *Elements of Software Science*. Elsevier.

- **Nejmeh, B.** (1988). "NPATH: A Measure of Execution Path Complexity
  and Its Applications." *Communications of the ACM*, 31(2), 188-200.
