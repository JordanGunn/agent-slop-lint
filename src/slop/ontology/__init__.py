"""slop.ontology — the project's vocabulary: what its words mean (W3C SKOS terms).

The lexicon says which words the code uses; the ontology says what words mean in the
project's domain, whether or not the code uses them. It is seeded from the code
(``draft``), agreed by people, and then holds the code to it.
"""
from __future__ import annotations

from .check import problems
from .fs import OntologyError, dump, load, parse, save
from .model import Scheme, Term

__all__ = ["OntologyError", "Scheme", "Term", "dump", "load", "parse", "problems", "save"]
