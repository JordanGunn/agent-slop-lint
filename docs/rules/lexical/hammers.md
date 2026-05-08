# lexical.hammers

**What it measures:** Identifier vocabulary against a
configurable banlist of catchall terms — `Manager`, `Helper`,
`Util`, `Spec`, `Object`, `Item`, `Data`, `Common`, `Core`, etc.
When all you have is a hammer, everything looks like a nail: the
codebase reaches for the same generic noun every time it needs
one, and every responsibility gets hammered into the same shape
regardless of fit.

> **v1.2.0 note.** Renamed from `lexical.weasel_words`. The
> hammer metaphor (Maslow's hammer) is sharper for what the rule
> catches: the agent has one tool of last resort and uses it as
> the tool of first resort.

**Default threshold:** any identifier matching a configured term
at a configured position. Per-term severity overrides; `exempt_when`
predicates suppress matches in test/main modules.

**Settings:**

| Setting | Default | Description |
|---|---|---|
| `terms` | (default profile) | List of term entries with per-term position config |

Each term entry:

| Field | Description |
|---|---|
| `word` | Term to match (case-insensitive against snake/Camel-split tokens) |
| `positions` | Subset of `"prefix"`, `"suffix"`, `"any"`, `"module_name"` |
| `severity` | Optional per-term override (`info` / `warning` / `error`) |
| `exempt_when` | Optional list: `"module_is_test"`, `"module_is_main"` |

## Default profile

| Term(s) | Positions | Severity | Notes |
|---|---|---|---|
| `Manager`, `Coordinator` | suffix | warning | DI-codebase legitimate; per-team tunable |
| `Helper`, `Utility`, `Util`, `Utils` | any, module_name | warning | almost never a real noun |
| `Handler`, `Processor` | suffix | info | sometimes legit |
| `Service`, `Provider`, `Engine` | suffix | info | DDD-controversial |
| `Factory`, `Builder` | suffix | info | named patterns; tunable |
| `Wrapper`, `Adapter` | suffix | info | sometimes pattern, sometimes drift |
| `Spec`, `Specification` | suffix | warning | reflexive agent term; exempt in tests |
| `Base` | suffix | warning | suspect when not actually abstract |
| `Abstract` | prefix | info | ABC pattern is legit |
| `Object`, `Item`, `Element`, `Thing` | suffix | error | zero semantic content |
| `Data`, `Info` | suffix | warning | restates obvious context |
| `Container`, `Holder` | suffix | warning | empties of meaning |
| `Common`, `Core`, `Misc`, `Extra`, `Shared` | module_name, suffix | warning | dumping-ground module names |
| `Stuff`, `Things` | any | error | always a smell |

## Position rationale

Same term is legit at one position and a smell at another:

- `Helper` as suffix (`MyHelper`) — agent reflex
- `Helper` as prefix (`HelperFoo`) — uncommon; usually wrong
- `Abstract` as prefix — ABC pattern
- `Abstract` as suffix (`FooAbstract`) — noise

A flat banlist would miss these distinctions. Per-word position
is essential.

## Configuration

```toml
[rules.lexical.hammers]
enabled = true
severity = "warning"   # default for terms without per-word override

[[rules.lexical.hammers.terms]]
word = "Manager"
positions = ["suffix"]
severity = "warning"

[[rules.lexical.hammers.terms]]
word = "Object"
positions = ["suffix"]
severity = "error"

[[rules.lexical.hammers.terms]]
word = "Spec"
positions = ["suffix"]
severity = "warning"
exempt_when = ["module_is_test"]
```

## Why "hammers"

Maslow's hammer ("if all you have is a hammer, everything looks
like a nail") is the canonical reference for the smell: a tool
applied to everything regardless of fit. `Manager`, `Helper`,
`Spec` are the developer's hammers — the term they reach for
when they don't have a real noun. The agent-noun-plural form
matches the rogues' gallery (`cowards`, `imposters`, `slackers`).
