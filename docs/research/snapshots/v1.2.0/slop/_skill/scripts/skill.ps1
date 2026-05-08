#!/usr/bin/env pwsh
# slop skill — agentic code quality linter
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillDir = Split-Path -Parent $ScriptDir

function Show-Help {
    @"
slop — agentic code quality linter

Commands:
  help       Show this help message
  validate   Verify slop is runnable
  schema     Emit JSON schema for .slop.toml
  run        Execute slop lint (JSON output)

Usage (run):
  skill.ps1 run --root <path>                Run all rules
  skill.ps1 run --root <path> --check <cat>  Run one category
  skill.ps1 run --bootstrap --root <path>    Init config if missing, then lint
"@
}

function Test-Validate {
    if (-not (Get-Command slop -ErrorAction SilentlyContinue)) {
        Write-Error "error: slop not found. Run 'pip install agent-slop-lint' or .\scripts\install.ps1"
        exit 1
    }
    $slopVer = & slop --version 2>$null
    Write-Output "slop: $slopVer"
    Write-Output "ok"
}

function Get-Schema {
    & slop schema
}

function Invoke-Run {
    param([string[]]$Arguments)

    $bootstrap = $false
    $checkTarget = ""
    $root = ""
    $passthrough = @()

    for ($i = 0; $i -lt $Arguments.Count; $i++) {
        switch ($Arguments[$i]) {
            "--bootstrap" { $bootstrap = $true }
            "--check" { $i++; $checkTarget = $Arguments[$i] }
            "--root" { $i++; $root = $Arguments[$i]; $passthrough += @("--root", $Arguments[$i]) }
            default { $passthrough += $Arguments[$i] }
        }
    }

    # Bootstrap: generate config if missing
    if ($bootstrap -and $root) {
        $configPath = Join-Path $root ".slop.toml"
        $pyprojectPath = Join-Path $root "pyproject.toml"
        if (-not (Test-Path $configPath)) {
            $hasTool = $false
            if (Test-Path $pyprojectPath) {
                $hasTool = (Select-String -Path $pyprojectPath -Pattern '\[tool\.slop\]' -Quiet) -eq $true
            }
            if (-not $hasTool) {
                Push-Location $root
                try { & slop init } finally { Pop-Location }
            }
        }
    }

    if ($checkTarget) {
        & slop check $checkTarget @passthrough --output json
    } else {
        & slop lint @passthrough --output json
    }
}

$command = if ($args.Count -gt 0) { $args[0] } else { "help" }

switch ($command) {
    "help" { Show-Help }
    "validate" { Test-Validate }
    "schema" { Get-Schema }
    "run" { Invoke-Run -Arguments ($args | Select-Object -Skip 1) }
    default {
        Write-Error "error: unknown command '$command'"
        Write-Error "run 'skill.ps1 help' for usage"
        exit 1
    }
}
