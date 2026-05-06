# lexical.weasel_words

**What it measures:** Identifier vocabulary against a configurable
banlist of catchall terms (`Manager`, `Helper`, `Util`, `Spec`,
`Object`, `Item`, `Data`, `Common`, `Core`, …). These single-word
agent tells appear when the agent needed a noun and didn't have one.
The harm is two-stage: the original miss, plus the gravitational sink
the catchall becomes for unrelated future responsibilities ("just
shove it in `FooManager`").

**Default threshold:** any identifier or module name matching a
configured term at a configured position. Per-term severity overrides;
exempt-when predicates suppress matches in test/main modules.

**Settings:**

| Setting | Default | Description |
|---|---|---|
| `terms` | (default profile) | List of term entries. Each entry: `word`, `positions`, `severity`, `exempt_when`. |

Each term entry has:

| Field | Description |
|---|---|
| `word` | Term to match (case-insensitive against tokens after snake/Camel split). |
| `positions` | List from `"prefix"`, `"suffix"`, `"any"`, `"module_name"`. |
| `severity` | Optional per-term severity override (`info` / `warning` / `error`). |
| `exempt_when` | Optional list of context predicates: `"module_is_test"`, `"module_is_main"`. |

## Default profile

| Term(s) | Positions | Severity | Notes |
|---|---|---|---|
| `Manager`, `Coordinator` | suffix | warning | DI codebases use legitimately; per-team tunable |
| `Helper`, `Utility`, `Util`, `Utils` | any, module_name | warning | almost never a real noun |
| `Handler`, `Processor` | suffix | info | sometimes a legit role |
| `Service`, `Provider`, `Engine` | suffix | info | DDD-legitimate; controversial in non-DDD |
| `Factory`, `Builder` | suffix | info | named patterns; tunable |
| `Wrapper`, `Adapter` | suffix | info | sometimes pattern, sometimes drift |
| `Spec`, `Specification` | suffix | warning | the canonical reflex agent term; exempt in tests |
| `Base` | suffix | warning | suspect when not actually abstract |
| `Abstract` | prefix | info | ABC pattern is legit |
| `Object`, `Item`, `Element`, `Thing` | suffix | error | zero semantic content |
| `Data`, `Info` | suffix | warning | restates obvious context |
| `Container`, `Holder` | suffix | warning | empties of meaning |
| `Common`, `Core`, `Misc`, `Extra`, `Shared` | module_name, suffix | warning | dumping-ground module names |
| `Stuff`, `Things` | any | error | always a smell |

## Position rationale

Position matters because the same term is a legit pattern at one
position and a smell at another:

- `Helper` as a suffix (`MyHelper`) is the agent reflex.
- `Helper` as a prefix (`HelperFoo`) is uncommon; usually a smell the
  other way.
- `Abstract` as a prefix is the ABC pattern.
- `Abstract` as a suffix (`FooAbstract`) is noise.

A flat banlist would miss these distinctions; the per-word position
list is essential.

## Custom config

```toml
[rules.lexical.weasel_words]
enabled = true
severity = "warning"   # default for any term without per-word override

[[rules.lexical.weasel_words.terms]]
word = "Manager"
positions = ["suffix"]
severity = "warning"

[[rules.lexical.weasel_words.terms]]
word = "Util"
positions = ["any", "module_name"]
severity = "warning"

[[rules.lexical.weasel_words.terms]]
word = "Object"
positions = ["suffix"]
severity = "error"     # zero semantic content; no excuse

[[rules.lexical.weasel_words.terms]]
word = "Spec"
positions = ["suffix"]
severity = "warning"
exempt_when = ["module_is_test"]
```

## Why "weasel words"

The term has decades of usage in English-prose criticism (technical
writing, journalism). It carries the right connotation: words that
*seem* informative but evade meaning. Compare with `catchall_terms`
(bland), `banned_terms` (focuses on mechanism), or `naming_drift`
(too abstract). The intent is immediately legible.
