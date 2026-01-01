<#
.SYNOPSIS
Agent orchestrator - executes specialized personas in the Bob Protocol system.

.DESCRIPTION
Invokes an agent (Morpheus, Neo, Trin, Oracle) to perform a specific task.
Manages state files, context loading, and delegation chaining.

.PARAMETER Agent
The agent persona to invoke: morpheus, neo, trin, oracle

.PARAMETER Task
The task type: architecture-review, implement, quality-gate, document-feature

.PARAMETER InputFile
Optional: JSON file with structured task input (overrides defaults)

.EXAMPLE
.\run-agent.ps1 -Agent morpheus -Task architecture-review
.\run-agent.ps1 -Agent neo -Task implement -InputFile agents/neo.docs/task_request.json

.NOTES
See .github/copilot-instructions.md for persona specifications
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("morpheus", "neo", "trin", "oracle")]
    [string]$Agent,

    [Parameter(Mandatory=$true)]
    [ValidateSet("architecture-review", "implement", "bugfix", "quality-gate", "test-implementation", "document-feature")]
    [string]$Task,

    [string]$InputFile = $null,
    [switch]$Verbose
)

# Configuration
$WORKSPACE_ROOT = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$AGENTS_DIR = Join-Path $WORKSPACE_ROOT "agents"
$AGENT_DOCS_DIR = Join-Path $AGENTS_DIR "$Agent.docs"
$CHAT_FILE = Join-Path $AGENTS_DIR "CHAT.md"
$CONTEXT_FILE = Join-Path $AGENT_DOCS_DIR "context.md"
$DELEGATION_FILE = Join-Path $AGENT_DOCS_DIR "next_delegation.json"
$LOG_FILE = Join-Path $AGENT_DOCS_DIR "execution.log"

# Ensure directories exist
if (-not (Test-Path $AGENT_DOCS_DIR)) {
    New-Item -ItemType Directory -Path $AGENT_DOCS_DIR -Force | Out-Null
}

# Helper functions
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    Write-Host $logMessage
    Add-Content -Path $LOG_FILE -Value $logMessage -ErrorAction SilentlyContinue
}

function Load-Context {
    if (Test-Path $CONTEXT_FILE) {
        return Get-Content $CONTEXT_FILE -Raw
    }
    return ""
}

function Post-ToChat {
    param([string]$Message)
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $entry = "`n[$timestamp] [$($Agent.ToUpper())] $Message"
    Add-Content -Path $CHAT_FILE -Value $entry
    Write-Log "Posted to CHAT.md: $Message"
}

function Update-Context {
    param([string]$Content)
    
    Set-Content -Path $CONTEXT_FILE -Value $Content -Force
    Write-Log "Updated context.md"
}

function Write-TaskRequest {
    param([hashtable]$Request)
    
    $requestJson = $Request | ConvertTo-Json -Depth 10
    $requestFile = Join-Path $AGENT_DOCS_DIR "task_request.json"
    Set-Content -Path $requestFile -Value $requestJson -Force
    Write-Log "Wrote task request: $requestFile"
    
    return $requestJson
}

# Main workflow
Write-Log "════════════════════════════════════════════════════════════════" "INFO"
Write-Log "Agent Invocation: $Agent / $Task" "INFO"
Write-Log "════════════════════════════════════════════════════════════════" "INFO"
Write-Log "Workspace: $WORKSPACE_ROOT"
Write-Log "Agent Docs: $AGENT_DOCS_DIR"

# Load or build task request
$taskRequest = @{
    agent = $Agent
    task = $Task
    timestamp = Get-Date -Format "o"
    status = "started"
}

if ($InputFile -and (Test-Path $InputFile)) {
    Write-Log "Loading input from: $InputFile"
    $inputContent = Get-Content $InputFile -Raw | ConvertFrom-Json
    $taskRequest += $inputContent
} else {
    Write-Log "Building default task request for: $Task"
    
    # Add default fields based on task type
    $taskRequest.Add("context_files", @("agents/$Agent.docs/context.md"))
    
    switch ($Task) {
        "architecture-review" {
            $taskRequest.Add("subject", "Design review - pending")
            $taskRequest.Add("constraints", @())
            $taskRequest.Add("blockers", @())
        }
        "implement" {
            $taskRequest.Add("objective", "Implementation pending")
            $taskRequest.Add("requirements", @())
            $taskRequest.Add("files_to_modify", @())
        }
        "quality-gate" {
            $taskRequest.Add("acceptance_criteria", @("tests pass", "ruff clean", "no blockers"))
        }
        "document-feature" {
            $taskRequest.Add("subject", "Documentation pending")
            $taskRequest.Add("audience", "ai-agents")
        }
    }
}

Write-TaskRequest $taskRequest

# Load context
$currentContext = Load-Context
Write-Log "Current context length: $($currentContext.Length) chars"

# Post start message to CHAT
Post-ToChat "*$($Agent.ToLower()) $Task started - see agents/$Agent.docs/context.md"

# Instructions for the agent
Write-Host @"
╔════════════════════════════════════════════════════════════════╗
║                    $Agent.ToUpper() - $Task                          ║
╚════════════════════════════════════════════════════════════════╝

📋 TASK REQUEST:
$(Write-Output $taskRequest | ConvertTo-Json -Depth 10)

📖 CONTEXT (from context.md):
---
$currentContext
---

💡 INSTRUCTIONS:
1. Read the task request above (JSON at the top)
2. Load context.md for background
3. Execute the task using available tools
4. Update context.md with results
5. Write next_delegation.json if delegating to another agent

📍 OUTPUT LOCATIONS:
  Context:      $CONTEXT_FILE
  Delegation:   $DELEGATION_FILE
  Chat Log:     $CHAT_FILE

🔗 REFERENCE:
  Instructions: .github/copilot-instructions.md
  Architecture: ntag424_sdm_provisioner/ARCH.md

⏱️  Press ENTER when complete...
"@

Read-Host "Agent $Agent waiting for completion"

# Check for delegation
if (Test-Path $DELEGATION_FILE) {
    $delegation = Get-Content $DELEGATION_FILE -Raw | ConvertFrom-Json
    Write-Log "Delegation detected: $($delegation.delegate_to) - $($delegation.task)" "INFO"
    Post-ToChat "Delegating to $($delegation.delegate_to) for $($delegation.task) ✓"
    
    # Auto-invoke next agent if configured
    Write-Host "`n⛓️  Auto-delegating to: $($delegation.delegate_to)`n"
    
    # Optional: invoke next agent automatically
    # & $PSScriptRoot\run-agent.ps1 -Agent $delegation.delegate_to -Task $delegation.task
} else {
    Write-Log "No delegation found - workflow complete" "INFO"
    Post-ToChat "Task complete - ready for next step ✓"
}

# Final status
Write-Log "════════════════════════════════════════════════════════════════" "INFO"
Write-Log "Agent execution complete" "INFO"
Write-Log "See agents/$Agent.docs/ for results" "INFO"
