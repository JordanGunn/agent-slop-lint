# structural.class.coupling

**What it measures:** Coupling Between Object Classes (Chidamber & Kemerer 1994) — the count of distinct external classes referenced by a class. High CBO means a class depends on many others and is fragile to change.

**Default threshold:** `CBO > 8`

**What the numbers mean:** A class with CBO=3 is focused. CBO=8 means it references 8 other classes — changes to any of them could break it. CBO=15+ is a strong signal of a class that's trying to do everything.

## What it prevents

A class that knows about everything. A change to any of those dependencies — a renamed method, a new required argument, a different return type — becomes a change that may break this class.

```python
# ❌ flagged (CBO = 12)
class OrderProcessor:
    def __init__(self):
        self.db        = Database()
        self.cache     = RedisCache()
        self.mailer    = EmailService()
        self.sms       = SMSGateway()
        self.fraud     = FraudDetector()
        self.tax       = TaxCalculator()
        self.inventory = InventoryService()
        self.shipper   = ShippingProvider()
        self.pdf       = InvoicePDF()
        self.slack     = SlackNotifier()
        self.metrics   = MetricsCollector()
        self.audit     = AuditLogger()
```

**When to raise it:** Facade or coordinator classes that legitimately reference many collaborators. Raising to 12–15 focuses on truly tangled classes.

**When to lower it:** Microservice or clean-architecture projects. CBO=5 enforces tight boundaries.

```toml
[rules.structural.class.coupling]
threshold = 8
```
