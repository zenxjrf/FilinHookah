# Dockerfile для Filin Bot v3.0
# Опционально: можно использовать вместо Python runtime на Render

FROM python:3.11-slim

# Рабочая директория
WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY . .

# Создание директорий для логов и бэкапов
RUN mkdir -p logs backups

# Порт (задаётся Render)
ENV PORT=10000

# Экспозиция порта
EXPOSE 10000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:$PORT/health')" || exit 1

# Запуск приложения
CMD ["uvicorn", "app.webapp.app:app", "--host", "0.0.0.0", "--port", "10000"]
