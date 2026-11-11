"""Where slop's files live. Constants more than one package needs go here.

A constant used by a single module stays in that module. It moves up to the ``layout`` of
its package when a second module in the package needs it, and to this file when a second
package does.
"""
from __future__ import annotations

#: The config file looked up from the scan root upward.
CONFIG_FILENAME = ".slop.toml"

#: The directory under a project root where slop keeps state it writes (the inference ledger,
#: the vocabulary).
STATE_DIR = ".slop"

#: The project's vocabulary, an Open Ontology JSON IR under ``STATE_DIR``.
ONTOLOGY_FILENAME = "ontology.json"
