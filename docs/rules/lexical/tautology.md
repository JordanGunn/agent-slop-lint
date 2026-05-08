# lexical.tautology

**What it measures:** Identifier suffixes that tautologically
restate their type annotation. `result_dict: dict[...]` — the
type system already says `dict`; the suffix is logically
tautologous with the annotation. `config_path: Path`,
`user_obj: User`, `data_str: str` — same pattern. Drop the
suffix; the annotation carries the type.

> **v1.2.0 note.** Renamed from `lexical.type_tag_suffixes`.
> The old name was a token-economy violation (3 underscored
> tokens per the spec). The new name names the smell directly:
> the suffix is a tautology of the type.

**Default threshold:** flag any annotated parameter whose
underscore-separated last token matches a recognised type-tag
suffix AND whose annotation contains the corresponding type
identifier. Severity `warning`.

**Settings:**

| Setting | Default | Description |
|---|---|---|
| `tag_to_types` | (default map) | Mapping from suffix → type identifiers |

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

Detection is restricted to identifiers ending in a recognised
type-tag suffix AFTER underscore parsing — `username` (one token)
doesn't trigger; `user_str` (two tokens, last is `str`) does.

Initial implementation covers Python only. Cross-language
extension is a deliberate follow-up.

## Configuration

```toml
[rules.lexical.tautology]
enabled = true
severity = "warning"
```

## Why "tautology"

The suffix and the type system say the same thing. In logic, a
tautology is a statement true by virtue of its form rather than
content; here, the identifier carries its type by restatement
rather than by naming. The suffix adds no information the
annotation didn't already carry.
