# slop — agentic code quality linter
# Installs slop + aux-skills backend and validates system dependencies
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$AuxDir = Join-Path (Split-Path -Parent $RootDir) "aux" "cli"

Write-Output "slop - Installation"
Write-Output "==================="
Write-Output ""

# -----------------------------------------------------------------------------
# Phase 1: Check system dependencies
# -----------------------------------------------------------------------------
Write-Output "Checking system dependencies..."

$errors = 0

# uv
if (Get-Command uv -ErrorAction SilentlyContinue) {
    $uvVersion = & uv --version 2>$null | Select-Object -First 1
    Write-Output "  + uv: $uvVersion"
} else {
    Write-Output "  x uv not found"
    Write-Output "    Install from: https://docs.astral.sh/uv/"
    $errors++
}

# ripgrep
if (Get-Command rg -ErrorAction SilentlyContinue) {
    $rgVersion = & rg --version 2>$null | Select-Object -First 1
    Write-Output "  + rg: $rgVersion"
} else {
    Write-Output "  x rg (ripgrep) not found"
    Write-Output "    Install: scoop install ripgrep | choco install ripgrep"
    $errors++
}

# fd
$hasFd = Get-Command fd -ErrorAction SilentlyContinue
$hasFdfind = Get-Command fdfind -ErrorAction SilentlyContinue
if ($hasFd) {
    $fdVersion = & fd --version 2>$null | Select-Object -First 1
    Write-Output "  + fd: $fdVersion"
} elseif ($hasFdfind) {
    $fdVersion = & fdfind --version 2>$null | Select-Object -First 1
    Write-Output "  + fdfind: $fdVersion"
} else {
    Write-Output "  x fd/fdfind not found"
    Write-Output "    Install: scoop install fd | choco install fd"
    $errors++
}

# git
if (Get-Command git -ErrorAction SilentlyContinue) {
    $gitVersion = & git --version 2>$null
    Write-Output "  + git: $gitVersion"
} else {
    Write-Output "  x git not found"
    $errors++
}

Write-Output ""

if ($errors -gt 0) {
    Write-Error "ERROR: $errors missing system dependencies."
    Write-Output "Please install the missing dependencies and re-run."
    exit 1
}

Write-Output "All system dependencies available."
Write-Output ""

# -----------------------------------------------------------------------------
# Phase 2: Install aux-skills (computational backend)
# -----------------------------------------------------------------------------
Write-Output "Installing aux-skills (computational backend)..."

$auxPyproject = Join-Path $AuxDir "pyproject.toml"
if (Test-Path $auxPyproject) {
    # Local development: install from sibling directory
    Push-Location $AuxDir
    try {
        & uv tool install --editable ".[dev]" --force --quiet
    } finally {
        Pop-Location
    }
    Write-Output "  + aux-skills installed from local path: $AuxDir"
} else {
    # Production: install from PyPI
    & uv tool install aux-skills --force --quiet
    Write-Output "  + aux-skills installed from PyPI"
}

Write-Output ""

# -----------------------------------------------------------------------------
# Phase 3: Install slop
# -----------------------------------------------------------------------------
Write-Output "Installing slop..."

$pyproject = Join-Path $RootDir "pyproject.toml"
if (-not (Test-Path $pyproject)) {
    Write-Error "ERROR: pyproject.toml not found at $RootDir"
    Write-Output "Ensure you're running this from the slop repository."
    exit 1
}

Push-Location $RootDir
try {
    & uv tool install --editable ".[dev]" --force --quiet
} finally {
    Pop-Location
}

Write-Output "  + slop installed (via uv tool)"
Write-Output ""

# -----------------------------------------------------------------------------
# Phase 4: Verify installation
# -----------------------------------------------------------------------------
Write-Output "Verifying installation..."

if (-not (Get-Command aux -ErrorAction SilentlyContinue)) {
    Write-Error "  x aux command not found in PATH"
    Write-Output "    You may need to add Scripts directory to PATH"
    exit 1
}
$auxVersion = & aux --version 2>$null
Write-Output "  + aux: $auxVersion"

if (-not (Get-Command slop -ErrorAction SilentlyContinue)) {
    Write-Error "  x slop command not found in PATH"
    Write-Output "    You may need to add Scripts directory to PATH"
    exit 1
}
$slopVersion = & slop --version 2>$null
Write-Output "  + slop: $slopVersion"

Write-Output ""

# -----------------------------------------------------------------------------
# Phase 5: Confirm rules
# -----------------------------------------------------------------------------
Write-Output "Available rules:"
& slop rules

Write-Output ""
Write-Output "==================="
Write-Output "Installation complete!"
Write-Output ""
Write-Output "Usage:"
Write-Output "  slop lint                         Run all rules with defaults"
Write-Output "  slop lint --root ./src            Scan a specific directory"
Write-Output "  slop lint --output json           JSON output for agents/CI"
Write-Output "  slop check complexity             Check one category"
Write-Output "  slop check class.coupling         Check one rule"
Write-Output "  slop init                         Generate .slop.toml config"
Write-Output ""
Write-Output "Configuration:"
Write-Output "  .slop.toml                        Project-level config"
Write-Output "  pyproject.toml [tool.slop]        Alternative config location"
Write-Output ""
