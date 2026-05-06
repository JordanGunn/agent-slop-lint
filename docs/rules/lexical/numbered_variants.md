# lexical.numbered_variants

**What it measures:** Function names ending in numeric suffixes
(`result1`, `attempt_2`, `_v3`) or alphabetic disambiguators
(`_old`, `_new`, `_local`, `_alt`, `_inner`, `_helper`, `_temp`).
These are agent tells for "named two related things by sequencing
them rather than describing what differs."

**Default threshold:** flag any function whose name ends with one of
the configured disambiguator patterns and whose stem has at least
`min_stem_tokens` tokens. Severity `warning`.

**Settings:**

| Setting | Default | Description |
|---|---|---|
| `min_stem_tokens` | `1` | Minimum number of tokens in the stem (filters out single-letter prefixes like `a1`). |
| `alpha_suffixes` | (see below) | Set of recognised alphabetic disambiguator suffixes. |

Default `alpha_suffixes`: `old`, `new`, `local`, `inner`, `alt`,
`helper`, `temp`, `tmp`, `copy`, `backup`, `orig`, `original`.

## What it surfaces

```python
# ❌ flagged
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

## False positives

Some legitimate names contain a recognised suffix (`get_localdate` is
treated correctly because the tokenizer splits on snake_case
boundaries, not regex match across the whole string). Loop and
math variables (`a1`, `x2`, `i_2`) are filtered by the
`min_stem_tokens` setting — raise it if you see noise from numbered
short stems.

```toml
[rules.lexical.numbered_variants]
enabled = true
severity = "warning"
min_stem_tokens = 1
```
