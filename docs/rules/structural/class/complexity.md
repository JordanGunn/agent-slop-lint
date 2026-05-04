# structural.class.complexity

**What it measures:** Weighted Methods per Class (Chidamber & Kemerer 1994) — the sum of CCX across all methods in a class. High WMC means the class is doing too much.

**Default threshold:** `WMC > 40`

**What the numbers mean:** A class with 10 methods averaging CCX=4 each has WMC=40. That is the boundary where a class is doing enough that a reader has to actively hold its pieces in their head. A class with WMC=150 is almost certainly a god class.

**Why the default is 40 and not 50.** The older industry convention of WMC > 50 was tuned for 1990s OO codebases where classes of 20-plus methods were routine. Contemporary OO advice (Fowler, Martin) treats classes with more than a handful of responsibilities as refactor candidates. 40 is closer to current practice and catches god-class drift earlier. If you maintain a codebase with legitimately large classes (framework base classes, protocol handlers), raising to 50 or 60 is reasonable.

## What it prevents

A class that collected every operation loosely related to a concept until nobody could say what it *doesn't* do. The complexity is real — it's just spread thin across many methods so no single one looks alarming.

```python
# ❌ flagged (WMC ≈ 55 — sum of all method CCX)
class UserManager:
    def register(self, data): ...          # CCX 4
    def login(self, creds): ...            # CCX 5
    def reset_password(self, email): ...   # CCX 4
    def update_profile(self, user): ...    # CCX 6
    def delete_account(self, user): ...    # CCX 3
    def verify_email(self, token): ...     # CCX 5
    def check_permissions(self, user, action): ...  # CCX 9
    def export_data(self, user): ...       # CCX 7
    def send_notification(self, user): ... # CCX 5
    def audit_log(self, event): ...        # CCX 7
    # … 6 more methods
```

**When to raise it:** Large classes that are well-factored internally (clear method boundaries, low coupling between methods). Raising to 75–100 focuses on the truly egregious cases.

**When to lower it:** Projects enforcing single-responsibility strictly. WMC=30 catches classes that are starting to accumulate responsibilities.

**When to disable:** Projects with no classes (pure functional style, Go without receiver types, scripting). WMC is meaningless if there are no classes.

```toml
[rules.structural.class.complexity]
threshold = 40
```
