# structural.complexity.npath

**What it measures:** Nejmeh's (1988) NPath complexity — the count of acyclic execution paths through a function. Unlike McCabe's CCX which is additive (each branch adds 1 to the count), NPath is multiplicative: sequential branches multiply path counts. Ten sequential independent `if` statements produce CCX=11 but NPath=1024. NPath catches combinatorial explosion that CCX massively underreports.

**Default threshold:** `NPath > 400`

**What the numbers mean:** A linear function has NPath=1. A single `if` doubles it to 2. A function with five sequential ifs has NPath=32; ten sequential ifs produces NPath=1024. The canonical Nejmeh (1988) threshold was 200, chosen because it corresponds to roughly the combinatorial limit of what fits in a reviewer's head.

**Why the default is 400 and not 200.** Nejmeh's 200 came from 1988 AT&T Bell Labs research on small pre-OO C functions before modern CLI dispatch patterns existed. Contemporary code routinely includes `main` functions with eight to ten subcommand branches (click, argparse, cobra), and each branch doubles NPath. Honest dispatch functions sit at NPath 256-512 and are not rot. 400 raises the floor above the typical CLI dispatch pattern while still flagging genuine combinatorial explosion (NPath > 500 and especially > 1000 almost always indicates branches that should have been decomposed into handler functions).

**When NPath differs from CCX:** CCX treats `if a: f(); if b: g(); if c: h()` as three independent decisions (CCX=4). NPath treats them as combinatorial because each branch independently affects whether the next one executes in a particular state (NPath=8). For code where the branches are genuinely independent, NPath is the more honest metric.

## What it prevents

Independent conditions that stack up until no single test can cover the full surface. The function looks simple to CCX — it barely branches — but each unrelated `if` doubles the number of input combinations a reviewer has to reason about.

```python
# ❌ flagged (NPath = 32, CCX = 6 — CCX misses this)
def validate_payload(data):
    if not data.get("name"):
        errors.append("missing name")
    if not data.get("email"):
        errors.append("missing email")
    if data.get("age", 0) < 18:
        errors.append("too young")
    if not data.get("consent"):
        errors.append("no consent")
    if data.get("country") not in ALLOWED:
        errors.append("blocked region")
    return errors
```

Five independent checks. Thirty-two combinations to test completely. CCX says 6. NPath says 32.

**When to raise it:** Parsers, validators, or code handling genuinely independent flags where combinatorial reasoning is intrinsic. Raising to 800 or 1000 accommodates legitimate branch fan-out.

**When to lower it:** Greenfield projects. NPath=200 returns to Nejmeh's canonical ceiling.

```toml
[rules.structural.complexity]
npath_threshold = 200
```
