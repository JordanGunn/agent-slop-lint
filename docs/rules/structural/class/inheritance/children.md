# structural.class.inheritance.children

**What it measures:** Number of Children (Chidamber & Kemerer 1994) — direct subclass count. A class with many children is a high-leverage change point — modifying its interface ripples to every child.

**Default threshold:** `NOC > 10`

**What the numbers mean:** NOC=3 is healthy polymorphism. NOC=10 means 10 subclasses depend on this parent's contract — any change to the parent is a blast radius of 10. NOC=20+ suggests the parent is being used as a dumping ground.

## What it prevents

A base class so widely subclassed that its interface can never be safely changed. Every modification is a blast radius across N subclasses.

```python
# ❌ flagged (NOC = 18)
class BaseExporter:
    def export(self, data): ...    # rename this parameter →
    def validate(self, data): ... # → 18 subclasses need updating

class CsvExporter(BaseExporter): ...
class JsonExporter(BaseExporter): ...
class XmlExporter(BaseExporter): ...
# … 15 more
```

**When to raise it:** Plugin architectures or type hierarchies where many implementations of a base are expected by design. Raising to 15–20 is appropriate.

**When to lower it:** Projects that want to catch growing hierarchies early. NOC=5 flags parents before the subclass count gets out of hand.

```toml
[rules.structural.class.inheritance.children]
threshold = 10
```
