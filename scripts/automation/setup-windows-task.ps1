# CardFlux Windows Task Scheduler Setup
# Run this as Administrator to create a scheduled task for daily updates

$TaskName = "CardFlux-DailyUpdate"
$ScriptPath = Join-Path $PSScriptRoot "update-orchestrator.mjs"
$NodePath = (Get-Command node).Source
$WorkingDir = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent

# Task configuration
$UpdateTime = "03:00"  # 3 AM daily
$Description = "CardFlux automated database update - scrapes latest TCG data, prices, and rebuilds indices"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CardFlux Windows Task Scheduler Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Task Name: $TaskName"
Write-Host "  Script: $ScriptPath"
Write-Host "  Node: $NodePath"
Write-Host "  Working Directory: $WorkingDir"
Write-Host "  Schedule: Daily at $UpdateTime"
Write-Host ""

# Check if task already exists
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($ExistingTask) {
    Write-Host "⚠️  Task already exists. Removing..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create the action
$Action = New-ScheduledTaskAction `
    -Execute $NodePath `
    -Argument $ScriptPath `
    -WorkingDirectory $WorkingDir

# Create the trigger (daily at specified time)
$Trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At $UpdateTime

# Create settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 4)

# Create principal (run with highest privileges)
$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Highest

# Register the task
$Task = Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description $Description

Write-Host ""
Write-Host "✅ Task created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Management Commands:" -ForegroundColor Yellow
Write-Host "  View task:    Get-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Run now:      Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Disable:      Disable-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Enable:       Enable-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Remove:       Unregister-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "View logs in: $WorkingDir\logs\updates" -ForegroundColor Cyan
Write-Host ""
Write-Host "To test immediately, run:" -ForegroundColor Yellow
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
Write-Host ""
