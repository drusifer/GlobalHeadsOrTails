#!/usr/bin/env pwsh
<#
.SYNOPSIS
    TIER 1: Quick Checks for TDD (Neo's workflow)
    
.DESCRIPTION
    Fast linting and testing for rapid development feedback.
    Target: <5 seconds
    
    Use this during active development:
    - After writing new code
    - Before committing
    - During TDD red-green-refactor cycles
    
.EXAMPLE
    .\scripts\lint-quick.ps1
#>

$ErrorActionPreference = "Stop"
$script:exitCode = 0

function Write-Step {
    param([string]$Message)
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan
}

function Run-Check {
    param(
        [string]$Name,
        [scriptblock]$Command
    )
    Write-Host "`n[$Name]" -ForegroundColor Yellow
    try {
        & $Command
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  FAILED" -ForegroundColor Red
            $script:exitCode = 1
        } else {
            Write-Host "  OK" -ForegroundColor Green
        }
    } catch {
        Write-Host "  ERROR: $_" -ForegroundColor Red
        $script:exitCode = 1
    }
}

# Activate venv and set cache prefix
$venvPython = ".\.venv\Scripts\python.exe"
$env:PYTHONPYCACHEPREFIX = Join-Path $PSScriptRoot "..\cache\pycache"

Write-Step "TIER 1: Quick Checks (TDD)"

# 1. Ruff check with auto-fix
Run-Check "Ruff Lint (auto-fix)" {
    & $venvPython -m ruff check src/ --fix --quiet
}

# 2. Ruff format
Run-Check "Ruff Format" {
    & $venvPython -m ruff format src/ --quiet
}

# 3. Fast pytest (fail fast, minimal output)
Run-Check "Pytest (fast-fail)" {
    & $venvPython -m pytest tests/test_provisioning_service.py tests/test_tui_flow.py tests/test_csv_key_manager.py -x -q --tb=no
}

Write-Host "`n"
if ($script:exitCode -eq 0) {
    Write-Host "ALL QUICK CHECKS PASSED" -ForegroundColor Green
} else {
    Write-Host "QUICK CHECKS FAILED" -ForegroundColor Red
}

exit $script:exitCode

