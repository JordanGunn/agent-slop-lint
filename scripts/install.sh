#!/usr/bin/env bash
# slop — agentic code quality linter
# Installs slop as a uv tool and validates system dependencies.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
SRC_DIR="$ROOT_DIR/src"

echo "slop — Installation"
echo "==================="
echo

# -----------------------------------------------------------------------------
# Phase 1: Check system dependencies
# -----------------------------------------------------------------------------
echo "Checking system dependencies..."

errors=0

# uv (required for installation)
if ! command -v uv &>/dev/null; then
    echo "  ✗ uv not found"
    echo "    Install from: https://docs.astral.sh/uv/"
    errors=$((errors + 1))
else
    echo "  ✓ uv: $(uv --version 2>/dev/null | head -1)"
fi

# ripgrep (required by slop's metric kernels)
if ! command -v rg &>/dev/null; then
    echo "  ✗ rg (ripgrep) not found"
    echo "    Install: apt install ripgrep | brew install ripgrep"
    errors=$((errors + 1))
else
    echo "  ✓ rg: $(rg --version 2>/dev/null | head -1)"
fi

# fd (required by slop's file discovery)
if command -v fd &>/dev/null; then
    echo "  ✓ fd: $(fd --version 2>/dev/null | head -1)"
elif command -v fdfind &>/dev/null; then
    echo "  ✓ fdfind: $(fdfind --version 2>/dev/null | head -1)"
else
    echo "  ✗ fd/fdfind not found"
    echo "    Install: apt install fd-find | brew install fd"
    errors=$((errors + 1))
fi

# git (required for hotspots)
if ! command -v git &>/dev/null; then
    echo "  ✗ git not found"
    echo "    Install: apt install git | brew install git"
    errors=$((errors + 1))
else
    echo "  ✓ git: $(git --version 2>/dev/null)"
fi

echo

if [[ $errors -gt 0 ]]; then
    echo "ERROR: $errors missing system dependencies."
    echo "Please install the missing dependencies and re-run."
    exit 1
fi

echo "All system dependencies available."
echo

# -----------------------------------------------------------------------------
# Phase 2: Install slop
# -----------------------------------------------------------------------------
echo "Installing slop..."

if [[ ! -f "$SRC_DIR/pyproject.toml" ]]; then
    echo "ERROR: pyproject.toml not found at $SRC_DIR"
    echo "Ensure you're running this from the slop repository."
    exit 1
fi

cd "$SRC_DIR"
uv tool install --editable ".[dev]" --force --quiet

echo "  ✓ slop installed (via uv tool)"
echo

# -----------------------------------------------------------------------------
# Phase 3: Verify installation
# -----------------------------------------------------------------------------
echo "Verifying installation..."

if ! command -v slop &>/dev/null; then
    echo "  ✗ slop command not found in PATH"
    echo "    You may need to add ~/.local/bin to PATH"
    exit 1
fi
echo "  ✓ slop: $(slop --version 2>/dev/null)"

echo

# -----------------------------------------------------------------------------
# Phase 4: Confirm rules
# -----------------------------------------------------------------------------
echo "Available rules:"
slop rules

echo
echo "==================="
echo "Installation complete!"
echo
echo "Usage:"
echo "  slop lint                         Run all rules with defaults"
echo "  slop lint --root ./src            Scan a specific directory"
echo "  slop lint --output json           JSON output for agents/CI"
echo "  slop check complexity             Check one category"
echo "  slop check class.coupling         Check one rule"
echo "  slop init                         Generate .slop.toml config"
echo
echo "Configuration:"
echo "  .slop.toml                        Project-level config"
echo "  pyproject.toml [tool.slop]        Alternative config location"
echo
