#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Project-specific virtual environment activation with custom settings.
    
.DESCRIPTION
    Activates the .venv and sets project-specific environment variables:
    - PYTHONPYCACHEPREFIX: Centralizes __pycache__ files in .cache/pycache/
    
.EXAMPLE
    . .\scripts\activate.ps1
#>

# Get the project root (parent of scripts folder)
$ProjectRoot = Split-Path -Parent $PSScriptRoot

# Activate the virtual environment
$VenvActivate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    . $VenvActivate
} else {
    Write-Error "Virtual environment not found at $VenvActivate"
    Write-Host "Run: python -m venv .venv"
    return
}

# Set PYTHONPYCACHEPREFIX to centralize __pycache__ files
$CacheDir = Join-Path $ProjectRoot ".cache\pycache"
if (-not (Test-Path $CacheDir)) {
    New-Item -ItemType Directory -Path $CacheDir -Force | Out-Null
}
$env:PYTHONPYCACHEPREFIX = $CacheDir

Write-Host "Activated with centralized pycache at: $CacheDir" -ForegroundColor Green

