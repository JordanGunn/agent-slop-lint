# Lexicon scaffolding (scratch)

Standalone scaffolding for the Lexeme + Lexicon classes that will
become the substrate under `src/cli/slop/_lexical/` once stable.
Kept here while the design is being exercised so the live package
isn't disturbed mid-refactor.

## Layout

```
scratch/lexicon/
├── __init__.py             # exports Lexeme, Lexicon, UNIVERSAL_NOISE
├── _naming.py              # split_identifier (copied from live tree)
├── lexeme.py               # Lexeme dataclass
├── lexicon.py              # Lexicon class
├── words.py                # UNIVERSAL_NOISE constant
└── tests/
    ├── test_lexeme.py
    └── test_lexicon.py
```

## Running tests

From repo root:

```bash
uv run --project src python -m pytest scratch/lexicon/tests/ -v
```

(Uses the project's pytest install; no separate venv needed.)

## Eventual destination

When the design is settled and the four group-B kernels
(`imposters`, `sprawl`, `slackers`, `confusion`) have been ported
to consume Lexeme/Lexicon:

- `lexeme.py`, `lexicon.py`, `words.py` → `src/cli/slop/_lexical/_words.py`
  (single module; small enough)
- `_naming.py` content stays in the live tree's `_lexical/_naming.py`
  (the live `split_identifier` is the source of truth — the copy
  here is for scaffolding isolation only)
- This `scratch/lexicon/` directory gets deleted

## Design references

- `docs/research/identifier-vocabulary.md` — layered ignore model,
  Newman 2017 + Fan 2023 rationale
- `docs/backlog/09.md` — per-language idiom layer, deferred
