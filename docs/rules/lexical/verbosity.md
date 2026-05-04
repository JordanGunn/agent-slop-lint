# lexical.verbosity

**What it measures:** Mean word-token count per identifier within a function. High verbosity (mean > 3.0) signals systemic naming bloat — `parsed_word_to_pdf_trimmed` rather than `parsed`.

**Default threshold:** mean > `3.0` word-tokens per identifier. Severity `warning`.

**What the numbers mean:** A function whose locals are mostly single-word names (`x`, `points`, `header`) lands around mean 1.0–1.5. A function leaning heavily on multi-token names (`extracted_lidar_point_x_coordinate`) crosses 3.0 quickly. The metric is a per-function aggregate, so one long name does not push a function over by itself.

## What it prevents

Every identifier tries to explain itself in full. By the time you've parsed a name you've lost track of what the function is actually doing.

```python
# ❌ flagged — mean token count ≈ 3.8
def parse_config(path):
    raw_configuration_file_contents = path.read_text()
    parsed_configuration_dictionary = json.loads(raw_configuration_file_contents)
    validated_configuration_result = validate(parsed_configuration_dictionary)
    return validated_configuration_result

# ✓ the function name already says "parse config"
def parse_config(path):
    raw = path.read_text()
    data = json.loads(raw)
    return validate(data)
```

**When to raise it:** Domains where compound names carry essential disambiguation (e.g. event-sourcing handlers like `on_user_account_balance_changed`). Raising to 4.0 leaves room for legitimate compound naming.

**When to lower it:** Greenfield projects pushing for terse, type-aware naming. Lowering to 2.5 catches verbosity drift earlier.

```toml
[rules.lexical.verbosity]
max_mean_tokens = 3.0
```
