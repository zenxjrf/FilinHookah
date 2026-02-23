FROM python:3.11-slim

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Python зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . .

# Создаём директорию для бэкапов
RUN mkdir -p backups

# Порт для Web App
EXPOSE 8000

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV LOG_PATH=logs.txt

# Запуск (можно переопределить в docker-compose)
CMD ["sh", "-c", "python -m app.run_webapp & python main.py"]
