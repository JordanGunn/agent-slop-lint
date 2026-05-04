# structural.complexity.cyclomatic

**What it measures:** McCabe's Cyclomatic Complexity (1976) — the number of linearly independent paths through a function. Each `if`, `for`, `while`, `case`, `catch`, and boolean operator (`&&`, `||`) adds a path.

**Default threshold:** `CCX > 10`

**What the numbers mean:**
- **1–10** — straightforward. Easy to test, easy to read.
- **11–20** — moderate. More paths means more test cases needed for coverage.
- **21–50** — complex. Refactor candidate. Hard to hold in your head.
- **51+** — untestable. Exhaustive path coverage is impractical.

## What it prevents

A function that branches so many ways you lose track of where you are. Every `if` is a fork you have to hold open in your head until the function ends — and writing tests that cover every path becomes practically impossible.

```python
# ❌ flagged (CCX ≈ 13)
def process_order(order):
    if order.type == "digital":
        if order.paid:
            if order.user.verified:
                send_download(order)
            else:
                flag_for_review(order)
        elif order.refunded:
            issue_credit(order)
        else:
            send_reminder(order)
    elif order.type == "physical":
        if order.paid:
            schedule_shipment(order)
        elif order.backordered:
            notify_delay(order)
        else:
            cancel(order)
    else:
        log_unknown(order)
```

**When to raise it:** Legacy codebases with many functions in the 11–15 range that are stable and well-tested. Raising to 15 silences noise without hiding real problems.

**When to lower it:** Greenfield projects or strict teams. A threshold of 6–8 forces smaller functions from the start.

```toml
[rules.structural.complexity]
cyclomatic_threshold = 10
```
