# lexical.cowards

**What it measures:** Identifiers ending in disambiguator suffixes —
numeric (`_1`, `_v2`, `_attempt3`) or alphabetic (`_old`, `_new`,
`_local`, `_alt`, `_inner`, `_helper`, `_temp`, `_copy`, `_backup`).
The codebase couldn't commit to one implementation, so it kept both,
marked with arbitrary suffixes that obscure what actually differs.

> **v1.2.0 note.** Renamed from `lexical.numbered_variants`.
> The old name was misleadingly narrow — the rule covers all
> disambiguator suffixes, not just numbered ones.

**Default threshold:** any function whose name ends in a
recognised disambiguator pattern, with stem ≥ `min_stem_tokens`
tokens. Severity `warning`.

**Settings:**

| Setting | Default | Description |
|---|---|---|
| `min_stem_tokens` | `1` | Minimum tokens in stem (filters loop vars `a1`, `x2`) |
| `alpha_suffixes` | (default set) | Alphabetic disambiguator suffixes |

Default `alpha_suffixes`: `old, new, local, inner, alt, helper,
temp, tmp, copy, backup, orig, original`.

## What it surfaces

```python
# ❌ flagged — disambiguator suffixes
def attempt_1(): ...
def attempt_2(): ...
def parse_old(): ...
def parse_new(): ...
def fetch_local(): ...      # often a copy-paste rename

# ✓ — describe what differs
def attempt_with_retry(): ...
def attempt_with_backoff(): ...
def parse_v1_format(): ...
def parse_v2_format(): ...
```

The smell isn't the existence of two related implementations —
it's the failure to express what differentiates them. `_v1`/`_v2`
hides the actual distinction; `_with_retry`/`_with_backoff`
expresses it. Provenance collapse vs provenance preservation.

## Configuration

```toml
[rules.lexical.cowards]
enabled = true
severity = "warning"
min_stem_tokens = 1
```

## Why "cowards"

The codebase didn't have the courage to pick one. Two related
things exist; instead of either replacing the old or describing
how the new differs, both are kept with arbitrary disambiguating
suffixes. The suffix marks the failure to commit.
