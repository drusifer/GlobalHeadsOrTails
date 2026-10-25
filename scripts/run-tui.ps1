<#
.SYNOPSIS
Launches the NTAG424 DNA SDM Provisioner TUI on Windows.

.DESCRIPTION
Configures the environment and launches the interactive Textual TUI.
Strictly requires the external persistent key service manager (default http://192.168.86.17:8080).
NEVER runs or spawns any local in-memory or background key service.

.PARAMETER Simulated
Set to run in simulated NFC mode without requiring physical ACR122 reader hardware.

.PARAMETER Url
URL of the persistent tag_validator_service (default: http://192.168.86.17:8080).

.EXAMPLE
.\scripts\run-tui.ps1
.\scripts\run-tui.ps1 -Simulated
.\scripts\run-tui.ps1 -Url http://192.168.86.17:8080
#>

param(
    [switch]$Simulated,
    [string]$Url = "http://192.168.86.17:8080"
)

$ErrorActionPreference = "Stop"

$workspaceRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $workspaceRoot ".venv\Scripts\python.exe"
$provisionTuiExe = Join-Path $workspaceRoot ".venv\Scripts\provision-tui.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "[ERROR] Virtual environment python not found at: $pythonExe" -ForegroundColor Red
    Write-Host "Please ensure the .venv is installed in the workspace root." -ForegroundColor Yellow
    exit 1
}

# 1. Target Key Service Configuration
$targetUrl = if ($env:TAG_VALIDATOR_URL) { $env:TAG_VALIDATOR_URL.TrimEnd('/') } else { $Url.TrimEnd('/') }
$env:TAG_VALIDATOR_URL = $targetUrl

# 2. Hardware / Simulation Mode
if ($Simulated) {
    $env:NTAG_SIMULATION = "1"
    Write-Host "[INFO] Running in SIMULATED NFC card mode (NTAG_SIMULATION=1)" -ForegroundColor Yellow
}
else {
    $env:NTAG_SIMULATION = "0"
    Write-Host "[INFO] Running in REAL HARDWARE mode (ACS ACR122 reader via PC/SC)" -ForegroundColor Cyan

    # HARDWARE SAFETY RULE: Forbid localhost when running on real hardware
    $uri = [System.Uri]$targetUrl
    if ($uri.Host -in @("localhost", "127.0.0.1", "::1")) {
        Write-Host ""
        Write-Host "================================================================================" -ForegroundColor Red
        Write-Host "CRITICAL HARDWARE KEY SAFETY RULE VIOLATION" -ForegroundColor Red
        Write-Host "================================================================================" -ForegroundColor Red
        Write-Host "Real hardware provisioning is pointed at localhost: '$targetUrl'" -ForegroundColor Red
        Write-Host "You CANNOT run real hardware provisioning against a local ephemeral service." -ForegroundColor Red
        Write-Host "Real hardware MUST ONLY talk to the real cluster key service manager (http://192.168.86.17:8080)." -ForegroundColor Red
        Write-Host "================================================================================" -ForegroundColor Red
        exit 1
    }

    # Verify real service health before allowing real hardware to run
    $healthUrl = "$targetUrl/healthz"
    Write-Host "[INFO] Verifying real key service manager at $healthUrl..." -ForegroundColor Cyan
    try {
        $resp = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 3 -ErrorAction Stop
        if ($resp.status -ne "ok") {
            Write-Host "[ERROR] Real key service manager responded with non-ok status: $($resp.status)" -ForegroundColor Red
            exit 1
        }
        Write-Host "[OK] Connected to real persistent key service manager at $targetUrl" -ForegroundColor Green
    }
    catch {
        Write-Host ""
        Write-Host "================================================================================" -ForegroundColor Red
        Write-Host "HARDWARE PROVISIONING BLOCKED: REAL KEY SERVICE IS DOWN OR UNREACHABLE" -ForegroundColor Red
        Write-Host "================================================================================" -ForegroundColor Red
        Write-Host "Cannot reach key service manager at $healthUrl" -ForegroundColor Red
        Write-Host "Details: $_" -ForegroundColor Yellow
        Write-Host "Real hardware cannot be provisioned without the persistent cluster service online." -ForegroundColor Red
        Write-Host "Start the cluster service manager on the cluster, or verify network route to 192.168.86.17." -ForegroundColor Yellow
        Write-Host "================================================================================" -ForegroundColor Red
        exit 1
    }
}

# 3. Launch TUI
Write-Host "[INFO] Launching SDM Provisioner TUI..." -ForegroundColor Green
if (Test-Path $provisionTuiExe) {
    & $provisionTuiExe
}
else {
    & $pythonExe -m sdm_provisioner.tui.tui_main
}
