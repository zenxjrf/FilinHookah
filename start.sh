#!/usr/bin/env bash
# Скрипт для запуска на Railway

# Устанавливаем переменную PORT если не задана
PORT=${PORT:-8000}
echo "Starting WebApp on port $PORT..."

# Запускаем WebApp в фоне
python -m app.run_webapp &
WEBAPP_PID=$!

# Запускаем бота в фоне
echo "Starting Telegram bot..."
python main.py &
BOT_PID=$!

# Ждём завершения любого из процессов
wait -n $WEBAPP_PID $BOT_PID

# Если один процесс упал, останавливаем другой
echo "One process exited, stopping others..."
kill $WEBAPP_PID 2>/dev/null
kill $BOT_PID 2>/dev/null
