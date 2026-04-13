# Setup Guide

Get slop running on your project in four steps: install, configure, integrate, verify.

## 1. Install

### Python package

slop is distributed as `agent-slop-lint` on PyPI. It pulls in [`aux-skills`](https://pypi.org/project/aux-skills/) (the computational backend) and all tree-sitter grammars automatically.

**Unix (macOS / Linux):**
```bash
pip install agent-slop-lint
```

**Windows (PowerShell):**
```powershell
pip install agent-slop-lint
```

### System dependencies

slop's metric kernels shell out to system tools that must be installed separately.

**Ubuntu / Debian:**
```bash
sudo apt-get install -y ripgrep fd-find git
```

**macOS (Homebrew):**
```bash
brew install ripgrep fd git
```

**Windows (Scoop):**
```powershell
scoop install ripgrep fd git
```

**Windows (Chocolatey):**
```powershell
choco install ripgrep fd git
```

| Tool | Purpose | Required |
|---|---|---|
| [ripgrep](https://github.com/BurntSushi/ripgrep) (`rg`) | Content search, symbol reference counting | Yes |
| [fd](https://github.com/sharkdp/fd) (`fd` / `fdfind`) | File discovery | Yes |
| [git](https://git-scm.com/) | Hotspot analysis (git log --numstat) | Yes |

Tree-sitter grammars are bundled as Python wheels — no manual grammar installation needed.

### Alternative: install script

The install script checks all dependencies, installs everything, and verifies your PATH.

**Unix:**
```bash
git clone https://github.com/JordanGunn/agent-slop-lint.git
cd agent-slop-lint
./scripts/install.sh
```

**Windows:**
```powershell
git clone https://github.com/JordanGunn/agent-slop-lint.git
cd agent-slop-lint
.\scripts\install.ps1
```

## 2. Configure

### Generate a config file

Run `slop init` in your project root to generate an annotated `.slop.toml` with sensible defaults:

**Unix:**
```bash
cd /path/to/your/project
slop init
```

**Windows:**
```powershell
cd C:\path\to\your\project
slop init
```

This creates `.slop.toml` with all 10 rules pre-configured. The defaults work well for most projects — you can tune later.

### Key settings to review

```toml
# Restrict to your project's languages (optional — default: all supported)
# languages = ["typescript"]

# Exclude paths that shouldn't be linted
# exclude = ["**/node_modules/**", "**/dist/**", "**/vendor/**"]

[rules.complexity]
cyclomatic_threshold = 10     # McCabe CCX — lower = stricter
cognitive_threshold = 15      # Campbell CogC — lower = stricter

[rules.hotspots]
since = "14 days ago"         # widen to "90 days ago" for human-pace repos

[rules.orphans]
enabled = false               # advisory — enable when ready for dead code audit
```

### Config priority

slop loads config in this order (first found wins):

1. `--config path/to/file` (explicit CLI flag)
2. `.slop.toml` (in project root)
3. `pyproject.toml` under `[tool.slop]`
4. Built-in defaults

### Alternative: pyproject.toml

If you prefer not to add another dotfile, configure slop in your existing `pyproject.toml`:

```toml
[tool.slop]
exclude = ["**/test_*", "**/vendor/**"]

[tool.slop.rules.complexity]
cyclomatic_threshold = 15
```

## 3. Integrate

Two paths, depending on how you want slop to run.

### Option A: Pre-commit hook (recommended for teams)

A pre-commit hook runs slop automatically before every commit. Nothing gets in without passing.

**Unix (`.git/hooks/pre-commit`):**
```bash
#!/bin/sh
slop lint --output quiet
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

**Windows (`.git/hooks/pre-commit`):**
```bash
#!/bin/sh
slop lint --output quiet
```

Git hooks on Windows use Git Bash, so the same shell script works. Alternatively, create `.git/hooks/pre-commit.ps1` and configure Git to use PowerShell:
```powershell
# .git/hooks/pre-commit
#!/bin/sh
powershell.exe -ExecutionPolicy Bypass -File "$(dirname "$0")/pre-commit.ps1"
```

```powershell
# .git/hooks/pre-commit.ps1
$result = slop lint --output quiet
if ($LASTEXITCODE -ne 0) { exit 1 }
```

**With the [pre-commit](https://pre-commit.com/) framework:**

Add to `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: local
    hooks:
      - id: slop
        name: slop lint
        entry: slop lint --output quiet
        language: system
        pass_filenames: false
        always_run: true
```

Then:
```bash
pre-commit install
```

### Option B: CI pipeline

Run slop as a CI gate. Exit code 0 = clean, 1 = violations.

**GitHub Actions (`.github/workflows/slop.yml`):**
```yaml
name: slop

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0    # full history for hotspot analysis

      - name: Install system dependencies
        run: sudo apt-get install -y -qq ripgrep fd-find git

      - name: Install slop
        run: pip install agent-slop-lint

      - name: Lint
        run: slop lint
```

**GitLab CI (`.gitlab-ci.yml`):**
```yaml
slop:
  image: python:3.12
  before_script:
    - apt-get update -qq && apt-get install -y -qq ripgrep fd-find git
    - pip install agent-slop-lint
  script:
    - slop lint
```

**Azure Pipelines:**
```yaml
steps:
  - script: |
      sudo apt-get update -qq
      sudo apt-get install -y -qq ripgrep fd-find git
      pip install agent-slop-lint
      slop lint
    displayName: 'slop lint'
```

**Important:** Use `fetch-depth: 0` (or equivalent) so git history is available for hotspot analysis. Shallow clones will trigger a warning and produce incomplete hotspot data.

### Option C: Agent skill (recommended for solo devs / Cursor users)

Load the slop skill into your agent configuration. The agent runs slop after structural changes and self-corrects before you see the diff — this is the "runs invisibly in the background" experience.

**Claude Code (`CLAUDE.md` or `.claude/commands/`):**

Add to your project's `CLAUDE.md`:
```markdown
## Code quality

After multi-file changes or refactors, run `slop lint --output json --root .` and address
any violations before presenting the result. If clean, say nothing. If violations exist,
fix them or flag the top offenders.
```

Or install the skill for richer passive/active behaviour:
```bash
# From the slop repo
./skills/slop/scripts/skill.sh init
```

**Cursor (`.cursorrules` or project rules):**
```
After making structural changes to the codebase (new files, refactors, multi-file edits),
run `slop lint --output json` and review the output. If there are violations:
- Fix complexity violations (CCX > 10, CogC > 15) by extracting functions
- Fix coupling violations (CBO > 8) by reducing cross-class references
- Report hotspot violations to the user
If clean, do not mention it.
```

**Windsurf / other agents:**

The pattern is the same for any agent that supports project-level instructions:
1. Tell the agent to run `slop lint --output json` after structural changes
2. Tell it to fix what it can and flag what it can't
3. Tell it silence is the report when clean

**How the two modes work:**

| Mode | Trigger | Behaviour |
|---|---|---|
| Passive | Agent just made multi-file changes | Run silently. If clean, say nothing. If violations, mention count + top offender and offer to fix. |
| Active | User asks "check quality" / "run the linter" | Report summary by category: violation counts, top 3 offenders per category. |

## 4. Verify

Confirm everything is working.

**Unix:**
```bash
# Check system tool availability
aux doctor

# List all rules and their thresholds
slop rules

# Dry run on your project
slop lint --root /path/to/your/project
```

**Windows:**
```powershell
aux doctor
slop rules
slop lint --root C:\path\to\your\project
```

**Expected output from `slop rules`:**
```
  complexity.cyclomatic            [on ] CCX > 10   Per-function Cyclomatic Complexity (McCabe 1976)
  complexity.cognitive             [on ] CogC > 15  Per-function Cognitive Complexity (Campbell 2018)
  complexity.weighted              [on ] WMC > 50   Per-class sum of method CCX (Chidamber & Kemerer 1994)
  hotspots                         [on ] 14d window Growth × complexity per file (Tornhill 2015)
  packages                         [on ] D' > 0.7   Package design distance (Martin 1994)
  deps                             [on ] cycles     Dependency cycle detection
  orphans                          [off]            Unreferenced symbols (advisory)
  class.coupling                   [on ] CBO > 8    Class coupling count (Chidamber & Kemerer 1994)
  class.inheritance.depth          [on ] DIT > 4    Inheritance tree depth (Chidamber & Kemerer 1994)
  class.inheritance.children       [on ] NOC > 10   Direct subclass count (Chidamber & Kemerer 1994)
```

## Supported languages

| Language | Extensions | All rules |
|---|---|---|
| Python | `.py` | Yes |
| JavaScript | `.js`, `.mjs`, `.cjs` | Yes |
| TypeScript | `.ts`, `.tsx` | Yes |
| Go | `.go` | Yes |
| Rust | `.rs` | Yes |
| Java | `.java` | Yes |
| C# | `.cs` | Yes |

The `packages` rule (Martin metrics) currently supports Go and Python only. All other rules work across all 7 languages.

## Troubleshooting

**`command not found: slop`** — pip installed to a directory not in your PATH. Try `python -m slop.cli` or add `~/.local/bin` (Unix) / `%APPDATA%\Python\Scripts` (Windows) to your PATH.

**`command not found: rg` / `fd`** — system dependencies not installed. See step 1.

**`git: not a git repository`** — the hotspots rule requires a git repo. Other rules work without git. Disable hotspots in `.slop.toml` if you're not in a repo:
```toml
[rules.hotspots]
enabled = false
```

**Shallow clone in CI** — hotspot analysis needs git history. Use `fetch-depth: 0` in your checkout step, or set `since` to a short window to reduce the history needed.

**`aux doctor` shows missing optional tools** — `httpx` and `trafilatura` are optional dependencies for `aux curl` (HTTP fetch). They're not needed by slop.
