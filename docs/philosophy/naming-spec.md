# Naming spec

## Why this document exists

The first composition rules slop shipped were named without a
proper discussion. `composition.affix_polymorphism`,
`composition.first_parameter_drift`, `composition.implicit_enum` —
names accumulated as the kernel grew, each one defensible in
isolation, none scrutinized as a set. When the time came to extend
the suite with three more rules, the cracks showed: one rule
violated slop's own substrate-naming convention, three carried
academic jargon where evocative single words would have been
clearer, and the suite name itself ("composition") was diagnostic
of the rules' *purpose* rather than their *substrate* — backwards
relative to slop's stated principle.

Catching this required actually sitting down and thinking about
what the names were doing. That is the irony of slop. The tool
plays on the internet-culture term "AI slop," but what it actually
catches is user complacency — the developer's failure to scrutinize
agent-produced artifacts that look fine in isolation. The names
slop accumulated were precisely such artifacts: each defensible at
the moment of addition, the set as a whole unconsidered. The
discipline of cleaning them up is the same discipline the tool
measures the absence of in the codebases it reads.

The naming spec exists so that future additions don't accumulate
the same way. It is the smallest piece of meta-rigor: rules about
how rules are named, written down, applied consistently.

## The substrate principle

Slop's three rule suites are named for **what they measure**, not
**what they imply** or **what technique they use**:

- `structural.*` — measures program structure (control flow, graphs)
- `information.*` — measures information density and readability
- `lexical.*` — measures vocabulary discipline (identifier strings,
  AST scope names)

This is stated in [`docs/rules/README.md`](../rules/README.md#naming-principle).
The principle is constitutive: a rule belongs in the suite whose
substrate it measures, regardless of what action it might recommend
or what concept it catches.

The original `composition.*` suite violated this. The rules within
all measured lexical artifacts (token edit distance, parameter-name
clustering, identifier alphabet recurrence). They were placed in
`composition.*` because they *imply* compositional refactoring —
the wrong axis. When that was caught, the whole suite collapsed
into `lexical.*` where the substrate placed it.

**Rule:** suite names describe substrate. If a rule's measurement
is on identifier tokens, it goes in `lexical.*`, even if its
implication is structural or compositional. The implication belongs
in the rule docs and the philosophy docs, not the suite name.

## Token economy

Every rule's name is a dotted path. Each segment between dots is a
**token**. Each token has rules:

- **Single word preferred.** `verbosity`, `tersity`, `stutter`,
  `sprawl`, `imposters`, `slackers`, `confusion`. A reader scanning
  the rule list can intuit each one before reading the docs.
- **Two-word compound tolerated.** `weasel_words`, `name_verbosity`,
  `boilerplate_docstrings`. Joined by underscore. Acceptable when
  no single word captures the smell.
- **Three-word never.** `type_tag_suffixes` was a violation —
  three tokens joined by underscores. Such names lose diagnostic
  energy: the reader doesn't intuit, they parse. If three words
  feel necessary, the smell isn't crisp enough yet — go back to
  the drawing board.

Hierarchical sub-rules are acceptable when a single dimension warrants
splitting (e.g., `lexical.stutter.{namespaces, callers, identifiers}`,
`lexical.sprawl.{scoped, global}`). Each level of the hierarchy
follows the token economy independently. Avoid hierarchies introduced
purely for grouping convenience without a real axis.

## Form: agent nouns over gerunds

When a rule's name describes a kind of *actor* visible in the code,
prefer the **agent-noun** form (typically `-ers`, `-ors`, `-ants`)
over the gerund form (`-ing`).

| Avoid (gerund) | Prefer (agent noun) |
|---|---|
| `squatting` | `squatters` |
| `crowding` | (no clean agent form; use abstract state noun like `confusion`) |
| `imposing` | `imposters` |
| `slacking` | `slackers` |
| `cowering` | `cowards` |
| `tagging` | (no good agent form; use `tautology` instead — abstract noun) |

The linguistic distinction:

- **Gerund** (verbal noun): names the action. `squatting` is
  what's being done.
- **Agent noun** (agentive noun): names the actor performing the
  action. `squatters` are the things doing it.
- **Abstract state noun**: names the property/state.
  `confusion`, `sprawl`, `dissonance`. No actor implied.

Slop's rules detect *artifacts* in the code — specific identifiers,
parameters, files, names. The diagnostic energy belongs on what's
*there* to point at. `lexical.imposters` tells the reader: this
rule finds imposters. The plural form is also intentional —
slop's detections are usually multiple instances of the same kind
of actor. Singular agent nouns (`lexical.imposter`) read as a
single instance and miss the population the rule actually
identifies.

When no clean agent-noun form exists, fall back to abstract state
nouns: `lexical.confusion`, `lexical.sprawl`, `lexical.tersity`,
`lexical.verbosity`. These describe the codebase's *state* rather
than naming actors within it. They're acceptable when the smell is
genuinely about the artifact's collective property rather than
about specific actors. Both `lexical.confusion` and a hypothetical
`lexical.confusers` would be defensible, but `confusion` is more
accurate to the rule's actual measurement (the lexicon is in a
state of confusion; there's no specific class of "confuser").

## Diagnostic energy: the name evokes the smell

A rule's name should let a reader who's never seen the rule
**intuit what's wrong** at first read. Slop's strongest names do
this:

- `lexical.stutter` — names that repeat their context. Read once,
  understood.
- `lexical.weasel_words` — vocabulary that evades meaning. The
  English-prose criticism term carries the right connotation.
- `lexical.boilerplate_docstrings` — docstrings that say nothing.
- `lexical.imposters` — parameters camouflaged as ordinary
  dependencies.
- `lexical.slackers` — siblings refusing to align without
  enforcement.
- `lexical.sprawl` — the closed alphabet that should be a type,
  scattered into name positions instead.

Bureaucratic names (`type_tag_suffixes`, `affix_polymorphism`,
`first_parameter_drift`) describe what's measured but require the
reader to translate measurement to smell. Diagnostic names
collapse that step.

This isn't a hard rule — some smells genuinely don't have an
evocative single word, and bureaucratic names are better than
twee or unclear names. But the *preference order* is:

1. Diagnostic single word (or two-word compound) — best
2. Bureaucratic but clear — acceptable
3. Twee or obscure — never

When in doubt, ask: would a developer who's never read slop's
docs guess what this rule catches? If yes, the name is doing its
job.

## The meta-irony as the leading principle

Slop catches user complacency. The complacency it catches is
specifically the human pattern of accepting agent-generated output
that looks fine on first read but accumulates problems across
additions. Each addition is locally defensible; the set is unconsidered.

This is exactly how slop's own rule names accumulated. Each name
defended itself. The set was never reviewed. When the set was
finally reviewed, the problems were obvious and easy to fix:
substrate violations, jargon, three-token names, missing diagnostic
energy.

The discipline of writing this spec — and applying it across all
existing and future rule names — is itself the discipline slop's
rules measure. The recursion is intentional: the tool that detects
the artifacts of unscrutinized addition has, by definition, to be
maintained with the scrutiny it demands.

When new rules are added in the future, the spec is the first
checkpoint. A name that requires explanation in the rule's own
docs to be understood is failing the spec. A name that violates
the substrate principle is failing the spec. A name with three
underscored tokens is failing the spec. These checks are cheap
and they prevent the kind of accumulated drift that the original
composition rules exemplified.

## The current taxonomy as worked example

Reading the current `lexical.*` rules in alphabetical order, the
names tell a story about identifier discipline:

```
lexical.boilerplate_docstrings    — docstrings that just restate the function name
lexical.confusion                 — scope holds multiple distinct lexicons
lexical.cowards                   — _v1, _v2, _old, _new — couldn't commit, kept both
lexical.imposters                 — parameters camouflaged as ordinary dependencies
lexical.name_verbosity            — names that overstate to compensate for missing namespace
lexical.singletons                — locals named once, used once, abandoned
lexical.slackers                  — siblings refusing to align without enforcement
lexical.sprawl.scoped             — closed alphabet sprawls within a scope
lexical.sprawl.global             — closed alphabet sprawls across the codebase
lexical.stutter                   — names repeating tokens from any enclosing scope
lexical.tautology                 — suffix tautologically restates the type
lexical.tersity                   — names too short to say anything
lexical.verbosity                 — names too long to read
lexical.weasel_words              — Manager, Helper, Spec, Util — naming surrender
```

Each name is in spec. Each name is diagnostic at first read. The
list as a whole reads as the agent's lexicon-of-failures: a
catalog of what naming looks like when no one is checking.

Note the rogues' gallery emerging in the agent-noun rules:
`cowards`, `imposters`, `singletons`, `slackers`. Each is a kind
of bad actor in the codebase, named directly. Reading the list
straight gives the diagnostic energy slop is built on — these are
the *kinds of things* that slip past unscrutinized review.

## When the spec applies

- **All new rules.** Any rule added after this spec is in force
  must conform.
- **Renames in flight.** Existing rules being renamed (the
  `composition.*` collapse, `lexical.type_tag_suffixes` →
  `lexical.tautology`, `lexical.numbered_variants` →
  `lexical.cowards`, `lexical.identifier_singletons` →
  `lexical.singletons`, `lexical.stutter.*` unified) must conform
  on the way out.
- **Existing rules that already conform.** No retroactive churn.
  The `lexical.*` rules from v1.1.0 that already follow the spec
  stay as-is.

The spec is not a license to relitigate every existing name. It's
a baseline for future addition and a tool for the small set of
existing renames that the composition collapse triggered.

## Open question: when the agent-noun and abstract forms both work

Some smells admit both an agent-noun form and an abstract state
noun. `lexical.confusers` vs `lexical.confusion`;
`lexical.sprawlers` vs `lexical.sprawl`. The current rules picked
abstract state nouns in both cases (`confusion`, `sprawl`) because
the smell is genuinely about the codebase's state rather than
about specific actors. Other cases will arise. The tiebreaker:
prefer the form that more directly names *what slop's measurement
returns*. If the rule output points at a discrete set of actors
(specific parameters, specific names), agent-noun. If the rule
output is a property of a region of code (a scope is confused; an
alphabet is sprawled), abstract state noun.

This isn't always crisp. When in doubt, write the rule message and
see which form reads naturally:

> "5 functions in `_compat.py` share `raw_rules` as first parameter.
>  These slackers refuse to align..."

vs

> "5 functions in `_compat.py` share `raw_rules` as first parameter.
>  This is slacking..."

The agent-noun form makes the rule message specific and pointable.
The abstract form generalizes. The first is preferable when the
rule's output points at specific code locations; the second when it
describes a property.
