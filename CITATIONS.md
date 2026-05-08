# Citations

slop is a small project with a long bibliography. This file records the
contributors that are not captured by the commit log.

## Academic and industrial sources

Every metric slop implements is the work of someone else. The full list of
papers, books, and authors is in [NOTICE](NOTICE), with the slop rule each
source backs and a deliberate per-default note where slop diverges from the
cited threshold. The shortest summary:

- McCabe (1976) — cyclomatic complexity
- Halstead (1977) — volume, difficulty
- Henry & Kafura (1981) — information flow (precursor to Martin's I/A/D')
- Nejmeh (1988) — NPath
- Chidamber & Kemerer (1994) — CK suite (CBO, DIT, NOC, WMC)
- Martin (1994, 2002) — Distance from the Main Sequence, Acyclic Dependencies Principle
- Lakos (1996) — physical design and the Acyclic Dependencies Principle
- Tornhill (2015) — hotspot analysis
- Campbell / SonarSource (2018) — cognitive complexity
- Tarjan (1972) — strongly-connected component algorithm used in cycle detection
- Newman et al. (2017) — empirical 14-identifier noise floor seeding the lexicon's UNIVERSAL_NOISE
- Fan, Arora & Treude (2023) — design principles: no universal stop list, binary removal can hurt

slop reimplements these formulas independently from tree-sitter ASTs. No code
from the original authors' implementations is used. See NOTICE for full
bibliographic entries.

## AI assistance

slop was written collaboratively with Augment Code's [auggie](https://docs.augmentcode.com/cli/overview)
agent CLI, using the Prism dynamic-routing setup that dispatches across three
frontier models depending on the task:

- **Claude Opus 4.7** (Anthropic) — primary architecture and rule design.
- **Claude Sonnet 4.5** (Anthropic) — implementation, refactoring, and test authoring.
- **Gemini 2.5 Pro** (Google DeepMind) — second-opinion review and cross-language kernel work.
- **Claude Code** (Anthropic) — agentic coding sessions, file editing, and CI triage.

Every metric kernel, threshold, and rule wrapper was reviewed and accepted by
a human before landing. The models did not invent the metrics; they helped
turn well-cited prior art into shipping code.

## Vendored kernels

The metric-kernel subpackages under `src/cli/slop/_fs/`, `_text/`, `_ast/`,
`_compose/`, `_structural/`, `_lexical/`, and `_util/` were originally
vendored from [aux-skills](https://github.com/JordanGunn/aux), also
Copyright 2025 Jordan Godau and licensed under Apache 2.0. See
[`src/cli/slop/KERNELS_LICENSE`](src/cli/slop/KERNELS_LICENSE) for the full
attribution text.

## Contributing

If you contribute and want your name added here, open a PR adding it. The
project follows the [all-contributors](https://allcontributors.org/) spirit
without (yet) the tooling.
