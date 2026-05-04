# structural.packages

**What it measures:** Robert C. Martin's (1994) Distance from the Main Sequence — how far a package's balance of abstractness (A) and instability (I) deviates from the ideal. D' = |A + I - 1|. A package in the "Zone of Pain" (D' > threshold, low A, low I) is concrete and depended on by many — hard to change.

**Default threshold:** `D' > 0.7`, fail on `pain` zone

**What the numbers mean:**
- **D' near 0** — on the Main Sequence. Balanced.
- **D' near 1** — in a zone. Either Pain (concrete + stable = rigid) or Uselessness (abstract + unstable = over-engineered).

**Currently supports:** Every language slop covers: Go, Python, Java, C#, TypeScript, JavaScript, Rust, Julia. Abstract-type detection is language-specific: Go interfaces, Python ABCs / Protocols, Java and C# `interface` plus `abstract class`, TypeScript `interface` plus `abstract class`, Rust `trait`, Julia `abstract type`. JavaScript has no `interface` or `abstract class` in the language itself, so every `class` is counted as concrete (Ja=0); this is accurate but means JS packages with `Ca > 0` will reliably land in Zone of Pain. Files in an unsupported language are silently skipped.

## What it prevents

Two failure modes at opposite extremes. A `utils` or `common` package that everything imports but contains no abstract types — concrete and load-bearing, impossible to change without breaking callers. Or a `ports` package full of abstract interfaces that nothing actually uses — over-engineered scaffolding for a future that never arrived.

```
# Zone of Pain — ❌ flagged (D' ≈ 0.9, low A, low I)
# src/utils/  ← imported by 40 other modules
#             ← 0 abstract classes
# Impossible to change without rippling everywhere.

# Zone of Uselessness — ❌ flagged (D' ≈ 0.9, high A, high I)
# src/ports/  ← imported by 0 other modules
#             ← 12 abstract Protocol classes
# Nobody is actually using these interfaces.
```

**When to raise it:** Mature codebases where some packages are legitimately concrete and stable (e.g., utility packages). Raising to 0.85 focuses on extreme cases.

**When to lower it:** Projects with strict layered architecture. 0.5 catches packages drifting from the ideal early.

**When to disable:** Single-package projects where the metric is ill-defined. JavaScript-only projects where you don't want the expected noise from the "no abstract concept" limitation; the rule is `severity = "warning"` by default, so it reports without failing the build.

```toml
[rules.structural.packages]
max_distance = 0.7
fail_on_zone = ["pain"]
severity = "warning"
```
