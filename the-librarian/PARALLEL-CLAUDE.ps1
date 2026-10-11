# PARALLEL-CLAUDE.ps1 - PowerShell script for Windows parallel execution
# This uses PowerShell's native parallel capabilities

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "PARALLEL CLAUDE EXECUTION - WINDOWS" -ForegroundColor Cyan
Write-Host "Using PowerShell Parallel Execution" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""

# First, let's check if Claude CLI is available and understand its options
Write-Host "Checking Claude CLI capabilities..." -ForegroundColor Yellow
$claudeHelp = claude --help 2>&1
Write-Host "Claude CLI found. Checking for batch/non-interactive options..." -ForegroundColor Green

# Create task directory
New-Item -ItemType Directory -Force -Path ".\tasks" | Out-Null

# Define the tasks as script blocks
$task1 = {
    $taskContent = @"
Based on docs/architecture.md, create the following Python files:

src/models/base.py - Base classes and enums
src/models/documents.py - Document, Chunk, ParsedDocument models (use Pydantic)
src/models/agents.py - AgentRequest, AgentResponse, Decision models
src/config.py - Settings using pydantic-settings

Also create:
- requirements.txt with needed packages
- .env.template with configuration variables

Make sure all code works and imports are correct.
"@

    # Try to run Claude with the task
    # Note: We don't know if --continue false works, testing different approaches
    $taskContent | claude chat 2>&1 | Out-File ".\logs\task1_models.log"
}

$task2 = {
    $taskContent = @"
Based on docs/subdomains/validation-engine.md, create:

src/validation/rules.py - Validation rule classes
src/validation/engine.py - ValidationEngine with validate_request()
tests/test_validation.py - Tests for validation

Mock database calls. Make all tests pass.
"@

    $taskContent | claude chat 2>&1 | Out-File ".\logs\task2_validation.log"
}

$task3 = {
    $taskContent = @"
Based on docs/architecture.md API section, create:

src/main.py - FastAPI application
src/api/agent.py - POST /agent/request-approval endpoint
src/api/health.py - GET /health endpoint

Server must run with: uvicorn src.main:app
Mock all database operations.
"@

    $taskContent | claude chat 2>&1 | Out-File ".\logs\task3_api.log"
}

# Method 1: Using Start-Process (Opens new windows)
function Start-ParallelClaude-NewWindows {
    Write-Host "Method 1: Opening new terminal windows..." -ForegroundColor Green

    # Create task files
    $task1Content | Out-File ".\tasks\task1.txt" -Encoding UTF8
    $task2Content | Out-File ".\tasks\task2.txt" -Encoding UTF8
    $task3Content | Out-File ".\tasks\task3.txt" -Encoding UTF8

    # Start new PowerShell windows
    Start-Process powershell -ArgumentList "-Command", "Get-Content .\tasks\task1.txt | claude chat; pause"
    Start-Process powershell -ArgumentList "-Command", "Get-Content .\tasks\task2.txt | claude chat; pause"
    Start-Process powershell -ArgumentList "-Command", "Get-Content .\tasks\task3.txt | claude chat; pause"
}

# Method 2: Using PowerShell Jobs (Background execution)
function Start-ParallelClaude-Jobs {
    Write-Host "Method 2: Using PowerShell background jobs..." -ForegroundColor Green

    $job1 = Start-Job -ScriptBlock $task1 -Name "Claude-Models"
    $job2 = Start-Job -ScriptBlock $task2 -Name "Claude-Validation"
    $job3 = Start-Job -ScriptBlock $task3 -Name "Claude-API"

    Write-Host "Jobs started. Monitoring progress..." -ForegroundColor Yellow

    while ($job1.State -eq 'Running' -or $job2.State -eq 'Running' -or $job3.State -eq 'Running') {
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 5
    }

    Write-Host ""
    Write-Host "All jobs completed!" -ForegroundColor Green

    # Get results
    Receive-Job -Job $job1
    Receive-Job -Job $job2
    Receive-Job -Job $job3
}

# Method 3: Using ForEach-Object -Parallel (PowerShell 7+)
function Start-ParallelClaude-Modern {
    Write-Host "Method 3: Using ForEach-Object -Parallel (PowerShell 7+)..." -ForegroundColor Green

    $tasks = @(
        @{Name="Models"; File="task1.txt"; Content=$task1Content},
        @{Name="Validation"; File="task2.txt"; Content=$task2Content},
        @{Name="API"; File="task3.txt"; Content=$task3Content}
    )

    $tasks | ForEach-Object -Parallel {
        $task = $_
        Write-Host "Starting task: $($task.Name)" -ForegroundColor Cyan
        $task.Content | claude chat 2>&1 | Out-File ".\logs\$($task.Name).log"
    } -ThrottleLimit 3
}

# Check PowerShell version
$psVersion = $PSVersionTable.PSVersion.Major
Write-Host "PowerShell Version: $psVersion" -ForegroundColor Yellow

# Provide options to user
Write-Host ""
Write-Host "Choose execution method:" -ForegroundColor Cyan
Write-Host "1. Open new windows (visual, easy to monitor)"
Write-Host "2. Background jobs (runs in background)"
if ($psVersion -ge 7) {
    Write-Host "3. Parallel ForEach (PowerShell 7+ only)"
}
Write-Host ""

$choice = Read-Host "Enter choice (1-3)"

switch ($choice) {
    "1" { Start-ParallelClaude-NewWindows }
    "2" { Start-ParallelClaude-Jobs }
    "3" {
        if ($psVersion -ge 7) {
            Start-ParallelClaude-Modern
        } else {
            Write-Host "PowerShell 7+ required for this option" -ForegroundColor Red
        }
    }
    default { Write-Host "Invalid choice" -ForegroundColor Red }
}