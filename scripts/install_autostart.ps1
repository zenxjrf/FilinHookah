param(
    [string]$TaskName = "FilinBotAutostart"
)

$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$runScript = Join-Path $projectRoot "run_local.ps1"
$startupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$startupCmd = Join-Path $startupDir "$TaskName.cmd"

if (-not (Test-Path $runScript)) {
    throw "run_local.ps1 not found: $runScript"
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$runScript`""

$trigger = New-ScheduledTaskTrigger -AtLogOn

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description "Autostart Filin Telegram bot and WebApp" `
        -Force | Out-Null

    Write-Host "Scheduled task '$TaskName' installed."
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "Scheduled task '$TaskName' started."
}
catch {
    $cmd = @"
@echo off
cd /d "$projectRoot"
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "$runScript"
"@
    Set-Content -Path $startupCmd -Value $cmd -Encoding Ascii
    Write-Host "Task Scheduler access denied. Startup fallback installed:"
    Write-Host $startupCmd
}
