# References

Full bibliography of the research slop's metrics are built on.

## Primary sources (metrics implemented in slop)

- **McCabe, T.J.** (1976). "A Complexity Measure." *IEEE Transactions on
  Software Engineering*, SE-2(4), 308-320.
  → `structural.complexity.cyclomatic`

- **Campbell, G.A.** (2018). "Cognitive Complexity: A new way of measuring
  understandability." SonarSource SA. Technical report.
  → `structural.complexity.cognitive`

- **Halstead, M.H.** (1977). *Elements of Software Science*. Elsevier.
  → `information.volume`, `information.difficulty`

- **Nejmeh, B.A.** (1988). "NPATH: A Measure of Execution Path Complexity
  and Its Applications." *Communications of the ACM*, 31(2), 188-200.
  → `structural.complexity.npath`

- **Chidamber, S.R. & Kemerer, C.F.** (1994). "A Metrics Suite for Object
  Oriented Design." *IEEE Transactions on Software Engineering*, 20(6),
  476-493.
  → `structural.class.complexity` (WMC),
  `structural.class.coupling` (CBO),
  `structural.class.inheritance.depth` (DIT),
  `structural.class.inheritance.children` (NOC)

- **Martin, R.C.** (1994). "OO Design Quality Metrics: An Analysis of
  Dependencies." *Proceedings of Workshop Pragmatic and Theoretical
  Directions in Object-Oriented Software Metrics*, OOPSLA '94.
  → `packages` (D', I, A)

- **Martin, R.C.** (2002). *Agile Software Development: Principles,
  Patterns, and Practices*. Prentice Hall. Chapter 20.
  → `packages` (expanded treatment), `deps` (Acyclic Dependencies Principle)

- **Lakos, J.** (1996). *Large-Scale C++ Software Design*. Addison-Wesley.
  → `deps` (Acyclic Dependencies Principle)

- **Tornhill, A.** (2015). *Your Code as a Crime Scene: Use Forensic
  Techniques to Arrest Defects, Bottlenecks, and Bad Design in Your
  Programs*. Pragmatic Bookshelf.
  → `hotspots`

- **Tarjan, R.E.** (1972). "Depth-First Search and Linear Graph
  Algorithms." *SIAM Journal on Computing*, 1(2), 146-160.
  → `deps` (SCC detection algorithm)

- **Wille, R.** (1982). "Restructuring lattice theory: an approach
  based on hierarchies of concepts." *Ordered Sets*, NATO Advanced
  Study Institutes Series 83, 445-470.
  → `composition.affix_polymorphism` (Formal Concept Analysis;
  inheritance lattice extraction)

- **Ganter, B. & Wille, R.** (1999). *Formal Concept Analysis:
  Mathematical Foundations*. Springer.
  → `composition.affix_polymorphism` (canonical FCA reference)

- **Caprile, B. & Tonella, P.** (2000). "Restructuring program
  identifiers based on word usage and stop-word filtering."
  *Proceedings of the 8th International Workshop on Program
  Comprehension*, 97-104.
  → `composition.affix_polymorphism` (identifier-pattern
  restructuring; affix detection)

- **Bavota, G., Oliveto, R., De Lucia, A., Antoniol, G., &
  Guéhéneuc, Y-G.** (2014). "Methodbook: Recommending Move Method
  Refactorings via Relational Topic Models." *IEEE Transactions on
  Software Engineering*, 40(7), 671-694.
  → `composition.first_parameter_drift` (Extract Class /
  Move Method refactoring detection lineage)

- **Harris, Z.S.** (1955). "From Phoneme to Morpheme." *Language*,
  31(2), 190-222.
  → `lexical.numbered_variants` (morpheme-boundary detection
  on identifiers; the segmentation principle behind suffix
  classification)

- **Lawrie, D., Feild, H., & Binkley, D.** (2006). "Quantifying
  Identifier Quality: An Analysis of Trends." *Empirical Software
  Engineering*, 12(4), 359-388.
  → `lexical.verbosity`, `lexical.tersity`, `lexical.name_verbosity`
  (identifier-quality metrics)

- **Deissenboeck, F. & Pizka, M.** (2006). "Concise and Consistent
  Naming." *Software Quality Journal*, 14(3), 261-282.
  → `lexical.weasel_words`, `lexical.boilerplate_docstrings`
  (naming-discipline foundations; concise-and-consistent rule)

- **Rissanen, J.** (1978). "Modeling by shortest data description."
  *Automatica*, 14(5), 465-471.
  → Methodology — MDL principle informs the
  `composition.affix_polymorphism` cluster filtering (a cluster
  earns its description length by reducing the codebase's
  description length).

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

