FROM python:3.11-slim

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    sqlite3 \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Python зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . .

# Создаём директорию для логов и БД
RUN mkdir -p backups

# Делаем скрипт запуска исполняемым
RUN chmod +x start.sh

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV LOG_PATH=logs.txt
ENV RAILWAY_DEPLOY_VERSION=2

# Запускаем скрипт
CMD ["bash", "start.sh"]
