FROM python:3.11-slim

WORKDIR /app

# Системные зависимости - меняем порядок чтобы сломать кэш
RUN apt-get update && apt-get install -y \
    bash \
    sqlite3 \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . .

# Очищаем кэш Python
RUN find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
RUN find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Создаём директорию для логов и БД
RUN mkdir -p backups

# Делаем скрипт запуска исполняемым
RUN chmod +x start.sh

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV LOG_PATH=logs.txt
ENV DEPLOY_VERSION=8

# Запускаем скрипт
CMD ["bash", "start.sh"]
