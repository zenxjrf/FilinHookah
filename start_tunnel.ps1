# Cloudflare Tunnel Background Launcher
$ErrorActionPreference = "SilentlyContinue"

cd "C:\Users\PC 2\PycharmProjects\Filin"

# Запуск cloudflared в фоновом режиме
Start-Process -FilePath ".\cloudflared.exe" `
  -ArgumentList "tunnel", "--url", "http://localhost:8000" `
  -WindowStyle Hidden `
  -PassThru

# Ожидание подключения
Start-Sleep -Seconds 10

# Получение URL
try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:20241/quicktunnel" -TimeoutSec 5
    $url = $response.hostname
    Write-Host "Cloudflare URL: https://$url"
    Write-Host "URL скопирован в буфер обмена!"
    $url | Set-Clipboard
} catch {
    Write-Host "Ошибка получения URL. Проверьте подключение к интернету."
}
