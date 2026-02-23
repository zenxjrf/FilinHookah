#!/bin/bash
# Скрипт быстрого деплоя на Yandex Cloud

set -e

echo "🚀 Деплой Filin Bot на Yandex Cloud"
echo "===================================="

# Проверка yc CLI
if ! command -v yc &> /dev/null; then
    echo "❌ Yandex Cloud CLI не установлен!"
    echo "Установи: https://cloud.yandex.ru/docs/cli/quickstart"
    exit 1
fi

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен!"
    echo "Установи: https://docs.docker.com/get-docker/"
    exit 1
fi

# Инициализация yc
echo "📝 Инициализация Yandex Cloud CLI..."
yc init

# Получение ID каталога
FOLDER_ID=$(yc config get folder-id)
echo "📁 Folder ID: $FOLDER_ID"

# Создание сервисного аккаунта (если нет)
echo "🔑 Создание сервисного аккаунта..."
SA_ID=$(yc iam service-account get --name filin-bot-sa --format json | jq -r '.id' 2>/dev/null || \
        yc iam service-account create --name filin-bot-sa --folder-id $FOLDER_ID --format json | jq -r '.id')
echo "✅ Service Account ID: $SA_ID"

# Создание Container Registry (если нет)
echo "📦 Создание Container Registry..."
REGISTRY_ID=$(yc container registry get --name filin-registry --format json | jq -r '.id' 2>/dev/null || \
              yc container registry create --name filin-registry --folder-id $FOLDER_ID --format json | jq -r '.id')
echo "✅ Registry ID: $REGISTRY_ID"

# Авторизация в Docker
echo "🐳 Авторизация в Docker..."
yc container registry configure --docker-for-registry-id $REGISTRY_ID

# Сборка образа
echo "🔨 Сборка Docker образа..."
docker build -t cr.yandex/$REGISTRY_ID/filin-bot:latest .

# Загрузка в реестр
echo "📤 Загрузка образа в реестр..."
docker push cr.yandex/$REGISTRY_ID/filin-bot:latest

# Создание контейнера (если нет)
echo "📥 Создание App Container..."
CONTAINER_ID=$(yc serverless container get --name filin-bot --format json | jq -r '.id' 2>/dev/null || \
               yc serverless container create --name filin-bot --folder-id $FOLDER_ID --format json | jq -r '.id')
echo "✅ Container ID: $CONTAINER_ID"

# Создание новой ревизии
echo "🔄 Создание новой ревизии..."

# Запрос переменных окружения
read -p "Введи BOT_TOKEN: " BOT_TOKEN
read -p "Введи WORKERS_CHAT_ID (или оставь пустым): " WORKERS_CHAT_ID
read -p "Введи ADMIN_IDS (или оставь пустым): " ADMIN_IDS

ADMIN_IDS=${ADMIN_IDS:-1698158035,987654321}

yc serverless container revision create \
  --container-name filin-bot \
  --image cr.yandex/$REGISTRY_ID/filin-bot:latest \
  --memory 256m \
  --cores 1 \
  --core-fraction 5 \
  --env BOT_TOKEN=$BOT_TOKEN \
  --env WEBAPP_URL=https://b8s6dqh7kqj7tqf7kqg7.mksrv.net \
  --env ADMIN_IDS=$ADMIN_IDS \
  --env WORKERS_CHAT_ID=${WORKERS_CHAT_ID:--1003748695791} \
  --env DATABASE_URL=sqlite+aiosqlite:///./filin.db \
  --env LOG_PATH=logs.txt

echo ""
echo "✅ Деплой завершён!"
echo ""
echo "📊 Проверить статус:"
echo "   yc serverless container get --name filin-bot"
echo ""
echo "📝 Посмотреть логи:"
echo "   yc serverless container logs --name filin-bot --tail 100"
echo ""
echo "🌐 URL будет доступен после деплоя в консоли Yandex Cloud"
