#!/usr/bin/env bash
# Скрипт для запуска на Railway

# Устанавливаем переменную PORT если не задана
export PORT=${PORT:-8000}
echo "Starting WebApp on port $PORT..."

# Сначала настраиваем webhook для бота
echo "Setting up Telegram webhook..."
python main.py || echo "Warning: webhook setup skipped (local mode)"

# Запускаем WebApp (он будет обрабатывать webhook от Telegram)
echo "Starting WebApp server..."
exec python -m app.run_webapp
