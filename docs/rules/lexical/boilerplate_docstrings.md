# lexical.boilerplate_docstrings

**What it measures:** Docstrings whose first-sentence content tokens
(after removing stop-words and generic function verbs) are a subset
of the function-name tokens. The signature already said this; the
docstring adds nothing.

**Default threshold:** flag when the docstring's content tokens
⊆ function-name tokens. Severity `warning`.

**Settings:**

| Setting | Default | Description |
|---|---|---|
| `extra_stopwords` | `[]` | Additional words to treat as content-free when comparing docstring against function name. |

## What it surfaces

```python
# ❌ flagged — "get the user email" tokens ⊆ {get, user, email}
def get_user_email():
    """Get the user email."""

# ❌ flagged
def parse_config():
    """Parses the config."""

# ✓ — adds information the name doesn't carry
def get_user_email():
    """Resolves canonical contact via the SSO directory."""

# ✓ — no docstring is fine; the name is sufficient
def get_user_email():
    return user.email
```

## Stop-word handling

The kernel ships a built-in stop-word list covering articles,
prepositions, copulas, and common ornamental function verbs (``get``,
``set``, ``return``, ``compute``, ``parse``, ``initialize``, …). A
docstring whose remaining content is *only* stop-words is also
boilerplate, but a different smell — the rule's specific target is
name-restatement, so pure-stop-word docstrings are not flagged.

## Scope

Initial implementation covers Python only. Other docstring
conventions (JSDoc, Javadoc, Doxygen) have radically different
shapes and are a deliberate follow-up.

```toml
[rules.lexical.boilerplate_docstrings]
enabled = true
severity = "warning"
```
