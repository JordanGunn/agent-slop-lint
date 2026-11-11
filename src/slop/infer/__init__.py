"""Inference as a controlled engineering primitive, layered over the linter.

Slop never calls a model. The host agent is the inferential instrument (``A``); this
package frames its work (``Dpre``), fixes the shape of what it may return (``S``), and
validates and routes the result (``Dpost``). Layers, bottom to top; an arrow is an import:

    bundle      the prose slop prints: instructions, references. Imports nothing in slop.
    contract    the wire types, their JSON Schema, and strict parsing. Imports nothing in slop.
    ledger      persisted rulings.                              imports contract
    frame       identity, location, fingerprint and rubric.      imports bundle, contract
    source      where residue comes from.                       imports contract, frame
    apply       validate, route, settle a report.               imports contract, frame, ledger, source

Only ``cli`` and ``skill`` import this package. New kinds of residue (a project survey for bootstrap, a
candidate listing) are new ``source`` modules; the layers above and below do not change.
"""
