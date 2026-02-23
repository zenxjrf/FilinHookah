$ErrorActionPreference = "Stop"

Set-Location -Path (Split-Path -Parent $MyInvocation.MyCommand.Path)

if (-not (Test-Path ".venv\\Scripts\\python.exe")) {
    throw "Python venv not found at .venv\\Scripts\\python.exe"
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ".env created from .env.example. Fill BOT_TOKEN first."
}

$envFile = Get-Content ".env" -Raw
if ($envFile -match "BOT_TOKEN=123456:replace-me") {
    throw "Set real BOT_TOKEN in .env before start."
}

Write-Host "Starting WebApp on http://localhost:8000 ..."
Start-Process -FilePath ".\\.venv\\Scripts\\python.exe" -ArgumentList "-m app.run_webapp"

Write-Host "Starting Telegram bot ..."
& .\.venv\Scripts\python.exe main.py
