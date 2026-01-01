#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Runs the full suite of linters and auto-fixers using the project's virtual environment.
#>

$ErrorActionPreference = "Continue"
$LogFile = "lint_report.txt"

Start-Transcript -Path $LogFile -Force

# Activate the environment
. "$PSScriptRoot\.venv\Scripts\Activate.ps1"

Write-Host "Running Ruff Check"
ruff check src/ --fix 2>&1 | Out-String
Write-Host "Running Ruff Format"
ruff format src/ 2>&1 | Out-String
Write-Host "Running Mypy"
mypy src/ 2>&1 | Out-String
Write-Host "Running Pylint"
pylint src/ 2>&1 | Out-String
Write-Host "Running Radon CC"
radon cc src/ -a -nc --total-average 2>&1 | Out-String
Write-Host "Running Radon MI"
radon mi src/ -s 2>&1 | Out-String
Write-Host "Running Vulture"
vulture src/ --min-confidence 80 2>&1 | Out-String
Write-Host "Running Bandit"
bandit -r src/ -ll 2>&1 | Out-String

Write-Host "`n=== Done. Log saved to $LogFile ===" -ForegroundColor Green

Stop-Transcript