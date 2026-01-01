<#
.SYNOPSIS
File watcher - automatically chains agent delegations.

.DESCRIPTION
Monitors agents/[agent].docs/next_delegation.json files.
When a delegation is detected, automatically invokes the next agent.
Enables seamless multi-agent workflows without manual intervention.

.EXAMPLE
.\watch-delegations.ps1

.NOTES
Run in background:
  .\watch-delegations.ps1 &

Stop with: Stop-Process -Name powershell -Filter {$_.MainWindowTitle -like "*watch*"}
#>

param(
    [int]$CheckIntervalSeconds = 3,
    [switch]$AutoDelegate
)

# Configuration
$WORKSPACE_ROOT = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$AGENTS_DIR = Join-Path $WORKSPACE_ROOT "agents"
$CHAT_FILE = Join-Path $AGENTS_DIR "CHAT.md"

$PERSONAS = @("morpheus", "neo", "trin", "oracle")
$PROCESSED_DELEGATIONS = @{}

Write-Host @"
╔════════════════════════════════════════════════════════════════╗
║              Agent Delegation Watcher Active                   ║
╚════════════════════════════════════════════════════════════════╝

📍 Monitoring: $AGENTS_DIR
⏱️  Check interval: $CheckIntervalSeconds seconds
🔗 Auto-delegate: $AutoDelegate

Watching for: agents/[persona].docs/next_delegation.json

Press Ctrl+C to stop watcher.

"@

# Watch loop
while ($true) {
    try {
        foreach ($persona in $PERSONAS) {
            $docsDir = Join-Path $AGENTS_DIR "$persona.docs"
            $delegationFile = Join-Path $docsDir "next_delegation.json"
            
            # Check if delegation file exists
            if (Test-Path $delegationFile) {
                # Read delegation
                $delegation = Get-Content $delegationFile -Raw | ConvertFrom-Json
                $delegationKey = "$($delegation.delegate_to)-$($delegation.task)"
                
                # Skip if already processed
                if ($PROCESSED_DELEGATIONS.ContainsKey($delegationKey)) {
                    continue
                }
                
                $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
                Write-Host "[$timestamp] 🔗 Delegation detected!"
                Write-Host "  From: $persona"
                Write-Host "  To:   $($delegation.delegate_to)"
                Write-Host "  Task: $($delegation.task)"
                Write-Host "  Context: $($delegation.context)"
                
                # Mark as processed
                $PROCESSED_DELEGATIONS[$delegationKey] = $true
                
                # Post to CHAT
                $chatEntry = "`n[$timestamp] [WATCHER] Delegating $persona → $($delegation.delegate_to) for $($delegation.task)"
                Add-Content -Path $CHAT_FILE -Value $chatEntry
                
                if ($AutoDelegate) {
                    Write-Host "  ⏳ Auto-invoking next agent...`n"
                    
                    # Invoke next agent
                    $scriptPath = Join-Path (Split-Path -Parent $PSScriptRoot) "scripts\run-agent.ps1"
                    $delegationJson = $delegation | ConvertTo-Json -Depth 10
                    $tempFile = Join-Path $docsDir "incoming_delegation.json"
                    Set-Content -Path $tempFile -Value $delegationJson -Force
                    
                    # Call next agent with delegation context
                    & $scriptPath -Agent $delegation.delegate_to -Task $delegation.task -InputFile $tempFile
                    
                    # Clean up delegation file
                    Remove-Item -Path $delegationFile -Force -ErrorAction SilentlyContinue
                }
            }
        }
        
        # Wait before next check
        Start-Sleep -Seconds $CheckIntervalSeconds
    }
    catch {
        Write-Host "⚠️  Error in watcher: $_" -ForegroundColor Yellow
        Start-Sleep -Seconds 5
    }
}
