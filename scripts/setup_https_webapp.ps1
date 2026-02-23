param(
    [int]$LocalPort = 8000
)

$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $projectRoot

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Python venv not found: $python"
}

$cloudflaredCandidates = @(
    (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe"),
    (Join-Path $projectRoot "cloudflared.exe")
)
$cloudflared = $cloudflaredCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $cloudflared) {
    Write-Host "Downloading cloudflared.exe ..."
    $cloudflared = Join-Path $projectRoot "cloudflared.exe"
    Invoke-WebRequest `
        -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" `
        -OutFile $cloudflared
}

try {
    & $cloudflared --version | Out-Null
}
catch {
    throw "cloudflared is present but not executable: $cloudflared"
}

Write-Host "Restarting local python processes for clean start ..."
Get-Process python -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -like "*PycharmProjects\Filin*" } |
    Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process cloudflared -ErrorAction SilentlyContinue |
    Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "Starting WebApp backend on port $LocalPort ..."
$web = Start-Process -FilePath $python -ArgumentList "-m app.run_webapp" -WorkingDirectory $projectRoot -PassThru

$tunnelLog = Join-Path $projectRoot "cloudflared.log"
$tunnelErr = Join-Path $projectRoot "cloudflared.err.log"
if (Test-Path $tunnelLog) {
    Remove-Item $tunnelLog -Force
}
if (Test-Path $tunnelErr) {
    Remove-Item $tunnelErr -Force
}

Write-Host "Starting HTTPS tunnel ..."
$tunnel = Start-Process -FilePath $cloudflared `
    -ArgumentList "tunnel --url http://localhost:$LocalPort --no-autoupdate" `
    -WorkingDirectory $projectRoot `
    -RedirectStandardOutput $tunnelLog `
    -RedirectStandardError $tunnelErr `
    -PassThru

$url = $null
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Milliseconds 500
    $content = ""
    if (Test-Path $tunnelLog) { $content += (Get-Content -Raw $tunnelLog) }
    if (Test-Path $tunnelErr) { $content += "`n" + (Get-Content -Raw $tunnelErr) }
    if ($content) {
        $match = [regex]::Match($content, "https://[a-zA-Z0-9\-]+\.trycloudflare\.com")
        if ($match.Success) {
            $url = $match.Value
            break
        }
    }
}

if (-not $url) {
    throw "Cannot get HTTPS tunnel URL. Check cloudflared.log and cloudflared.err.log"
}

Write-Host "Tunnel URL: $url"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

$envText = Get-Content -Raw ".env"
if ($envText -match "(?m)^WEBAPP_URL=") {
    $envText = [regex]::Replace($envText, "(?m)^WEBAPP_URL=.*$", "WEBAPP_URL=$url")
}
else {
    $envText = $envText.TrimEnd() + "`r`nWEBAPP_URL=$url`r`n"
}
Set-Content -Path ".env" -Value $envText -Encoding Ascii

Write-Host "Starting bot ..."
$bot = Start-Process -FilePath $python -ArgumentList "main.py" -WorkingDirectory $projectRoot -PassThru

Write-Host "DONE"
Write-Host "WEBAPP_PID=$($web.Id)"
Write-Host "TUNNEL_PID=$($tunnel.Id)"
Write-Host "BOT_PID=$($bot.Id)"
Write-Host "WEBAPP_URL=$url"
