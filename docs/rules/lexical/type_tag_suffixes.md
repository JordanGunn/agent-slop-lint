# lexical.type_tag_suffixes

**What it measures:** Identifiers whose suffix re-states the type
annotation. ``result_dict: dict[str, int]`` — the type system already
says `dict`; the suffix is ornamentation. ``config_path: Path``,
``user_obj: User``, ``data_str: str`` — same pattern. The fix is
always "drop the suffix; the annotation carries the type."

**Default threshold:** flag any annotated parameter whose
underscore-separated last token matches a recognised type-tag suffix
AND whose annotation contains the corresponding type identifier.
Severity `warning`.

**Settings:**

| Setting | Default | Description |
|---|---|---|
| `tag_to_types` | (default map) | Mapping from suffix → set of type identifiers that match. |

Default `tag_to_types`:

| Suffix | Matching annotations |
|---|---|
| `_dict` | `dict`, `Dict`, `Mapping`, `Map` |
| `_list` | `list`, `List`, `Sequence`, `Iterable`, `Tuple` |
| `_set` | `set`, `Set`, `FrozenSet` |
| `_tuple` | `tuple`, `Tuple` |
| `_str` | `str`, `String` |
| `_path` | `Path`, `PathLike`, `PurePath`, `PosixPath` |
| `_obj` | `object`, `Object`, `Any` |
| `_data` | `bytes`, `bytearray`, `Buffer` |
| `_int` | `int`, `Integer`, `Long` |
| `_float` | `float`, `Float`, `Double` |
| `_bool` | `bool`, `Boolean` |

## What it surfaces

```python
# ❌ flagged
def render(result_dict: dict[str, int]) -> None: ...
def write(config_path: Path) -> None: ...

# ✓
def render(result: dict[str, int]) -> None: ...
def write(config: Path) -> None: ...

# ✓ — `username` is a domain term, not a type tag
def lookup(username: str) -> User: ...
```

## Implementation note

Detection is restricted to identifiers ending in a recognised type-tag
suffix AFTER underscore parsing — `username` (one token) doesn't
trigger; `user_str` (two tokens, last is `str`) does.

Initial implementation covers Python only — Python has the most
universal explicit-annotation conventions. Cross-language extension
is a deliberate follow-up.

```toml
[rules.lexical.type_tag_suffixes]
enabled = true
severity = "warning"
```
