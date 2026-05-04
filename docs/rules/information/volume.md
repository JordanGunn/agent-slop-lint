# information.volume

**What it measures:** Halstead's (1977) Volume metric — `V = Length × log2(Vocabulary)`, where Length is total operator/operand occurrences and Vocabulary is the distinct-operator + distinct-operand count. Volume proxies the information content of a function. Large Volume means "a lot of stuff is happening in here."

**Default threshold:** `V > 1500`

**What the numbers mean:** Volume scales with both size and diversity. A 20-line function with five variables and standard arithmetic lands around V=150. A 60-line function touching twenty symbols and many operators can hit V=1200 without looking obviously complex to CCX or CogC. That is the niche Halstead covers.

**Why the default is 1500 and not 1000.** SonarSource-style V > 1000 is a reasonable boundary for functions that were *meant* to be decomposed. In practice, legitimate orchestration code (format_human, run_lint, dispatch functions, serializers that touch many fields) often sits in the 1200-1800 range without being rot. 1500 still flags the pathological case where three responsibilities fused into one function (typical V of 2000-plus) while leaving honest orchestration alone.

## What it prevents

A function that isn't obviously complex — no deep nesting, no many branches — but touches so many distinct variables and operations that you can't hold it all in working memory at once. CCX stays low; Volume catches it.

```python
# ❌ flagged (V ≈ 2100 — high symbol diversity, not just line count)
def render_invoice(order, customer, config, locale, template):
    symbol   = locale.currency_symbol
    rate     = config.tax_rates[customer.region]
    subtotal = sum(item.price * item.qty for item in order.line_items)
    discount = order.discount_code.value if order.discount_code else 0
    tax      = (subtotal - discount) * rate
    total    = subtotal - discount + tax
    header   = template.render_header(customer.name, order.id, locale.date_fmt)
    rows     = [template.render_row(i, locale) for i in order.line_items]
    footer   = template.render_footer(subtotal, discount, tax, total, symbol)
    return template.assemble(header, rows, footer, config.page_size)
```

**When to raise it:** Long formatters, serializers, or state-machine dispatchers that legitimately reference many symbols. Raising to 2000 leaves room for breadth-heavy code.

**When to lower it:** Greenfield projects wanting tight function sizes. Lowering to 1000 or 800 forces decomposition early.

**When Halstead differs from CCX:** CCX counts control-flow paths. Halstead counts tokens. A function with low CCX but 40 unique operands (e.g. a big dict construction) will have high Volume but low CCX. Halstead catches that; CCX misses it.

```toml
[rules.information.volume]
threshold = 1500
```
