---
name: slop
license: Apache-2.0
description: >
  Agentic code quality linter. Runs 10 structural analysis rules against a
  codebase and reports violations. Operates in passive mode (after changes,
  surface only if violations found) or active mode (on user request, report
  summary). Backed by tree-sitter, ripgrep, fd, and git.
metadata:
  author: Jordan Godau
  version: 0.1.0
  references:
    - references/01_SUMMARY.md
    - references/02_INTENT.md
    - references/03_POLICIES.md
    - references/04_PROCEDURE.md
  scripts:
    - scripts/skill.sh
    - scripts/skill.ps1
  keywords:
    - slop
    - linter
    - complexity
    - coupling
    - hotspots
    - code-quality
    - agentic
    - ci
---

# INSTRUCTIONS

> **Do not read reference files directly.**
> Run `./scripts/skill.sh init` to load all references in a single call.

1. Run `./scripts/skill.sh init` and follow the instructions.
