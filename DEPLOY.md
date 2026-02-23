# 🚀 Деплой на Yandex Cloud

## 📋 Шаг 1: Регистрация в Yandex Cloud

1. Перейди на [cloud.yandex.ru](https://cloud.yandex.ru)
2. Войди через Яндекс аккаунт
3. Привяжи карту (дадут 5000 ₽ грант на 60 дней)

---

## 📋 Шаг 2: Установка Yandex Cloud CLI

### Windows (PowerShell от имени администратора):
```powershell
Invoke-WebRequest -Uri https://storage.yandexcloud.net/ycloud-cli/1.56.0/yandex-cli-windows-amd64.exe -OutFile yc.exe
```

Или через chocolatey:
```powershell
choco install yandex-cloud
```

### Инициализация:
```bash
yc init
```

---

## 📋 Шаг 3: Создание сервисного аккаунта

```bash
# Создаём сервисный аккаунт
yc iam service-account create --name filin-bot

# Даём права на Container Registry
yc resource-manager folder add-access-binding --role container-registry.editor --subject serviceAccount:<ID_сервисного_аккаунта>

# Создаём API ключ
yc iam key create --service-account-id <ID_сервисного_аккаунта> --output key.json
```

---

## 📋 Шаг 4: Создание Container Registry

```bash
# Создаём реестр
yc container registry create --name filin-registry

# Запоминаем ID реестра
yc container registry get --name filin-registry

# Авторизуемся в Docker
yc container registry configure --docker-for-registry-id <ID_реестра>
```

---

## 📋 Шаг 5: Сборка и загрузка Docker образа

```bash
# Собираем образ
docker build -t cr.yandex/<ID_реестра>/filin-bot:latest .

# Загружаем в реестр
docker push cr.yandex/<ID_реестра>/filin-bot:latest
```

---

## 📋 Шаг 6: Создание Cloud Function (или App Container)

### Вариант A: Cloud Functions (дешевле, ~100-200 ₽/мес)

```bash
yc serverless function create --name filin-bot

yc serverless function version create \
  --function-name filin-bot \
  --runtime python:311 \
  --entrypoint main.handler \
  --memory 256m \
  --execution-timeout 30s \
  --service-account-id <ID_сервисного_аккаунта> \
  --environment BOT_TOKEN=<твой_токен> \
  --environment WEBAPP_URL=<твой_URL> \
  --environment ADMIN_IDS=1698158035,987654321 \
  --environment WORKERS_CHAT_ID=<ID_чата> \
  --source-path .
```

### Вариант B: App Container (надёжнее, ~300-500 ₽/мес) ⭐ Рекомендую

```bash
yc serverless container create --name filin-bot

yc serverless container revision create \
  --container-name filin-bot \
  --image cr.yandex/<ID_реестра>/filin-bot:latest \
  --memory 256m \
  --cores 1 \
  --core-fraction 5 \
  --service-account-id <ID_сервисного_аккаунта> \
  --env BOT_TOKEN=<твой_токен> \
  --env WEBAPP_URL=<твой_URL> \
  --env ADMIN_IDS=1698158035,987654321 \
  --env WORKERS_CHAT_ID=<ID_чата> \
  --env DATABASE_URL=sqlite+aiosqlite:///./filin.db
```

---

## 📋 Шаг 7: Настройка домена и HTTPS

### Для App Container:
```bash
# Создаём эндпоинт
yc serverless container gateway create --name filin-gateway

# Привязываем домен (опционально)
yc serverless container gateway update --name filin-gateway --domain твой-домен.ru
```

**HTTPS работает автоматически!**

---

## 📋 Шаг 8: Обновление .env

После деплоя обнови `.env`:

```env
BOT_TOKEN=8306362120:AAHXCXOXFk_Eam6gbfnwK0f0vTyI16RNFZo
DATABASE_URL=sqlite+aiosqlite:///./filin.db
WEBAPP_URL=https://<твой-контейнер>.serverless.yandexcloud.net
ADMIN_IDS=1698158035,987654321
WORKERS_CHAT_ID=-1003748695791
LOG_PATH=logs.txt
DEFAULT_SCHEDULE=Ежедневно с 14:00 до 2:00
DEFAULT_CONTACTS=Phone: +7 (000) 000-00-00\nAddress: Example street, 1
```

---

## 📋 Шаг 9: Обновление бота в Telegram

1. Открой @BotFather
2. `/mybots` → FilinHookah_bot
3. **Menu Button** → отправь новый URL: `https://<твой-контейнер>.serverless.yandexcloud.net`

---

## 💰 Стоимость (после гранта):

| Ресурс | Стоимость |
|--------|-----------|
| App Container (256MB, 1 core) | ~250 ₽/мес |
| Container Registry | ~50 ₽/мес |
| Cloud Logging | ~20 ₽/мес |
| **Итого** | **~320-400 ₽/мес** |

---

## 🔧 Полезные команды:

```bash
# Посмотреть логи
yc serverless container logs --name filin-bot --tail 100

# Перезапустить контейнер
yc serverless container revision create --container-name filin-bot --image cr.yandex/<ID>/filin-bot:latest

# Остановить контейнер
yc serverless container update --name filin-bot --status STOPPED
```

---

## ⚠️ Важные моменты:

1. **SQLite** работает, но для production лучше PostgreSQL
2. **Файлы** (logs.txt, filin.db) сохраняются между перезапусками
3. **Таймаут** — контейнер работает постоянно, бот не "засыпает"
4. **HTTPS** — работает автоматически через Yandex Cloud

---

## 🆘 Если что-то пошло не так:

1. Проверь логи: `yc serverless container logs --name filin-bot`
2. Проверь переменные окружения в консоли Yandex Cloud
3. Убедись, что бот имеет доступ к интернету
4. Проверь токен бота в @BotFather

**Удачи с деплоем! 🚀**
