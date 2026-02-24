#!/usr/bin/env bash
# Скрипт для запуска на Railway

echo "=========================================="
echo "=== FILIN HOOKAH STARTUP SCRIPT ==="
echo "=========================================="
echo "PORT=$PORT"
echo "WEBAPP_URL=$WEBAPP_URL"
echo "=========================================="

# Устанавливаем переменную PORT если не задана
export PORT=${PORT:-8000}
echo "Starting WebApp on port $PORT..."

# Сначала настраиваем webhook для бота
echo "Setting up Telegram webhook..."
echo "Running: python setup_webhook.py"
python setup_webhook.py 2>&1
WEBHOOK_EXIT=$?
echo "setup_webhook.py exited with code: $WEBHOOK_EXIT"

# Запускаем WebApp (он будет обрабатывать webhook от Telegram)
echo "Starting WebApp server..."
python -m app.run_webapp
