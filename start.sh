#!/usr/bin/env bash
# Скрипт для запуска на Render

echo "=========================================="
echo "=== FILIN HOOKAH STARTUP ==="
echo "=========================================="
echo "PORT=$PORT"
echo "WEBAPP_URL=$WEBAPP_URL"
echo "=========================================="

# Запускаем ТОЛЬКО Web App
exec python -m app.run_webapp
