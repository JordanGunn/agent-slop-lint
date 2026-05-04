# structural.class.inheritance.depth

**What it measures:** Depth of Inheritance Tree (Chidamber & Kemerer 1994) — levels of parent classes above a given class. Deep hierarchies make behaviour hard to predict because methods can be overridden at any level.

**Default threshold:** `DIT > 4`

**What the numbers mean:** DIT=1 means one parent (common). DIT=4 means four levels deep — changes to any ancestor can subtly change this class's behaviour. DIT=7+ is a code smell in virtually any project.

## What it prevents

Inheritance chains so deep that the actual behaviour of a class is scattered across six parent files. You can't answer "what does this method do?" without opening every ancestor.

```python
# ❌ flagged (DIT = 6)
class Base: ...
class Configurable(Base): ...
class Serializable(Configurable): ...
class Persistable(Serializable): ...
class Auditable(Persistable): ...
class UserModel(Auditable): ...
# To understand UserModel.save(), you have to read all six.
```

**When to raise it:** Framework-heavy codebases (e.g., Django models inherit from multiple framework bases). Raising to 6 accommodates framework depth without masking project-level inheritance problems.

**When to lower it:** Projects that favor composition over inheritance. DIT=2 catches any inheritance beyond the immediate base class.

```toml
[rules.structural.class.inheritance.depth]
threshold = 4
```
