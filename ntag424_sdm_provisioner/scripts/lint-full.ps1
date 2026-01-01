#!/usr/bin/env pwsh
<#
.SYNOPSIS
    TIER 2: Full QA Gate for Sprint Acceptance (Trin's workflow)
    
.DESCRIPTION
    Thorough quality checks for shipping a sprint.
    Includes slower checks, complexity analysis, and full test suite.
    
    Use this before:
    - Merging to main
    - Shipping a sprint
    - Code review approval
    
.EXAMPLE
    .\scripts\lint-full.ps1
    
.EXAMPLE
    .\scripts\lint-full.ps1 -SkipSlowTests
#>

param(
    [switch]$SkipSlowTests,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"
$script:exitCode = 0
$script:warnings = @()

function Write-Step {
    param([string]$Message)
    Write-Host "`n" -NoNewline
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host "  $Message" -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor Cyan
}

function Run-Check {
    param(
        [string]$Name,
        [scriptblock]$Command,
        [switch]$WarnOnly
    )
    Write-Host "`n[$Name]" -ForegroundColor Yellow
    $startTime = Get-Date
    try {
        $output = & $Command 2>&1
        $duration = ((Get-Date) - $startTime).TotalSeconds
        
        if ($Verbose -or $LASTEXITCODE -ne 0) {
            Write-Host $output
        }
        
        if ($LASTEXITCODE -ne 0) {
            if ($WarnOnly) {
                Write-Host "  WARNING (${duration:F1}s)" -ForegroundColor Yellow
                $script:warnings += $Name
            } else {
                Write-Host "  FAILED (${duration:F1}s)" -ForegroundColor Red
                $script:exitCode = 1
            }
        } else {
            Write-Host "  OK (${duration:F1}s)" -ForegroundColor Green
        }
    } catch {
        Write-Host "  ERROR: $_" -ForegroundColor Red
        if (-not $WarnOnly) {
            $script:exitCode = 1
        }
    }
}

# Activate venv and set cache prefix
$venvPython = ".\.venv\Scripts\python.exe"
$env:PYTHONPYCACHEPREFIX = Join-Path $PSScriptRoot "..\cache\pycache"

Write-Step "TIER 2: Full QA Gate (Sprint Acceptance)"

# ============================================================================
# SECTION 1: Code Quality (must pass)
# ============================================================================
Write-Step "Section 1: Code Quality"

Run-Check "Ruff Lint (strict - no auto-fix)" {
    & $venvPython -m ruff check src/
}

Run-Check "Ruff Format Check" {
    & $venvPython -m ruff format src/ --check
}

# ============================================================================
# SECTION 2: Complexity Analysis (warnings only)
# ============================================================================
Write-Step "Section 2: Complexity Analysis"

Run-Check "Radon Cyclomatic Complexity (C+ grade)" -WarnOnly {
    # Show only functions with complexity grade C or worse (11+)
    & $venvPython -m radon cc src/ -a -nc --total-average
}

Run-Check "Radon Maintainability Index" -WarnOnly {
    # Show files with MI below B grade
    & $venvPython -m radon mi src/ -nb
}

# ============================================================================
# SECTION 3: Design Quality (warnings only)
# ============================================================================
Write-Step "Section 3: Design Quality"

Run-Check "Pylint Duplicate Code" -WarnOnly {
    & $venvPython -m pylint src/ --disable=all --enable=R0801 --exit-zero
}

Run-Check "Pylint Design Smells" -WarnOnly {
    # R0902: too-many-instance-attributes (God class)
    # R0903: too-few-public-methods (data class smell)
    # R0913: too-many-arguments
    # R0914: too-many-locals
    & $venvPython -m pylint src/ --disable=all --enable=R0902,R0903,R0913,R0914 --exit-zero
}

Run-Check "Prospector (comprehensive)" -WarnOnly {
    & $venvPython -m prospector src/ --strictness medium --without-tool pep257 --without-tool pyroma
}

# ============================================================================
# SECTION 4: Test Suite
# ============================================================================
Write-Step "Section 4: Test Suite"

Run-Check "Core Tests (must pass)" {
    & $venvPython -m pytest tests/test_provisioning_service.py tests/test_tui_flow.py tests/test_csv_key_manager.py tests/test_crypto_validation.py -v --tb=short
}

if (-not $SkipSlowTests) {
    Run-Check "Full Test Suite" -WarnOnly {
        & $venvPython -m pytest tests/ -v --tb=short
    }
} else {
    Write-Host "`n[Full Test Suite] SKIPPED (-SkipSlowTests)" -ForegroundColor Gray
}

# ============================================================================
# SUMMARY
# ============================================================================
Write-Host "`n"
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "  SUMMARY" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan

if ($script:warnings.Count -gt 0) {
    Write-Host "`nWarnings:" -ForegroundColor Yellow
    foreach ($w in $script:warnings) {
        Write-Host "  - $w" -ForegroundColor Yellow
    }
}

Write-Host "`n"
if ($script:exitCode -eq 0) {
    Write-Host "FULL QA GATE PASSED - Ready to ship!" -ForegroundColor Green
} else {
    Write-Host "FULL QA GATE FAILED - Fix issues before shipping" -ForegroundColor Red
}

exit $script:exitCode

