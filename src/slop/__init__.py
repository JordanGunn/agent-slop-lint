"""slop: a linter and code-structure tool for source trees, built on tree-sitter.

From the bottom up: ``span`` and ``identity`` say where code is and what a scope is called;
``ast`` parses files and holds one grammar per language; ``lexicon`` splits identifiers into
words; ``scope`` carves the sources into a tree of corpus, realms, packages, modules, classes
and callables; ``metrics`` and ``graph`` measure that tree; ``ontology`` and ``lexical`` hold the
project's vocabulary and compare it with the code; ``rule``, ``rules``, ``dispatch``,
``violation`` and ``config`` are the linter; ``cli`` and ``skill`` are the ways in.
"""
