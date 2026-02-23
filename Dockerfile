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

# Копируем проект с пересозданием
COPY . .
RUN rm -rf __pycache__ app/__pycache__ app/*/__pycache__ 2>/dev/null || true

# Создаём директорию для логов и БД
RUN mkdir -p backups

# Делаем скрипт запуска исполняемым
RUN chmod +x start.sh

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV LOG_PATH=logs.txt
ENV DEPLOY_VERSION=5

# Запускаем скрипт
CMD ["bash", "start.sh"]
