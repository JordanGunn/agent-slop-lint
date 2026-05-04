# structural.hotspots

**What it measures:** Growth-weighted complexity per file — Tornhill's (2015) hotspot framework with LOC delta as the churn proxy. Score = `sum_ccx × max(0, net_loc_delta)`. Files that are complex AND growing fast are where architectural damage accumulates.

**Default:** `14 days ago` window, `min_commits = 2`, fail on `hotspot` quadrant

**Key settings:**

| Setting | Default | Description |
|---|---|---|
| `since` | `"14 days ago"` | How far back to look. The 14-day default is tuned for agentic work — agents accumulate rot in days, not months. |
| `min_commits` | `2` | Files touched only once in the window are filtered out as noise. |
| `fail_on_quadrant` | `["hotspot"]` | Which quadrants trigger a violation. |

**Quadrants explained:**
- **hotspot** — complex AND growing fast. The worst case. Always worth investigating.
- **stable_complex** — complex but not growing. Legacy code. Not urgent.
- **churning_simple** — growing fast but not complex. Watch it — complexity follows growth.
- **calm** — low on both axes. No action needed.

## What it prevents

Files where new logic keeps getting piled on top of old logic. Complexity alone is survivable. Churn alone is manageable. Together, they mark the files most likely to contain the bug you're about to introduce.

```
# a file that's both complex and actively growing:
# git log --oneline -- src/core/engine.py | wc -l  →  47 commits in 14 days
# structural.complexity.cyclomatic: CCX = 28

# slop flags it as a hotspot.
# Every new commit here lands in code that's already hard to reason about.
```

**When to widen the window:** Human-pace repos where 14 days captures too little. Set `since = "90 days ago"` or `since = "6 months ago"`.

**When to add quadrants to fail_on:** Teams that want to catch `churning_simple` files before they become hotspots: `fail_on_quadrant = ["hotspot", "churning_simple"]`.

**When to disable:** Repos with no git history, or when running on a shallow clone where history is unavailable.

```toml
[rules.structural.hotspots]
since = "14 days ago"
min_commits = 2
fail_on_quadrant = ["hotspot"]
```
