# 🦉 Filin Telegram Bot + Mini App v3.1

**Информационный** Telegram-бот для кальянного заведения на `aiogram 3` с мини-приложением на `FastAPI` + `PostgreSQL`.

## 🚀 Что нового в v3.1

### ✨ Новые возможности:
- ✅ **Информационный режим** - красивая витрина заведения
- ✅ **Звонок по клику** - бронирование через телефон
- ✅ **Рассылки** - отправка уведомлений клиентам
- ✅ **Кэширование** - ускорение API в 4 раза

### 📊 Улучшения:
- ⚡ Время ответа API: ~200ms → ~50ms (**4x быстрее**)
- 📡 Синхронизация: Polling 5s → WebSocket (**Real-time**)

---

## 📋 Что реализовано

### Клиентский функционал:
- ✅ Информация о заведении: описание, преимущества, условия
- ✅ Меню: акции, график, контакты, меню кальянов
- ✅ Программа лояльности (5-й кальян -50%, 10-й - бесплатно)
- ✅ Бронирование через звонок по клику
- ✅ Автоматическая подписка на рассылку при /start

### Админ-панель:
- ✅ Команды: `/admin`, `/dashboard`, `/broadcast`, `/subscribers`
- ✅ Статистика подписчиков
- ✅ Рассылки (текст, фото, видео)
- ✅ Управление клиентами: `/check_client`, `/add_visits`
- ✅ Управление контентом: `/set_schedule`, `/set_contacts`, `/add_promo`

### Техническая часть:
- ✅ PostgreSQL + SQLite (адаптивный движок)
- ✅ Connection pooling (оптимизировано для Render)
- ✅ Кэширование запросов (TTL 30 секунд)
- ✅ Lazy loading для связанных моделей
- ✅ APScheduler для напоминаний
- ✅ Rate limiting middleware

---

## 🏗️ Структура проекта

```
Filin/
├── main.py                    # Точка входа (polling/webhook)
├── app/
│   ├── config.py              # Настройки (PostgreSQL pool)
│   ├── run_bot.py             # Запуск бота
│   ├── run_webapp.py          # Запуск WebApp сервера
│   ├── db/
│   │   ├── base.py            # SQLAlchemy + connection pool
│   │   ├── models.py          # ORM модели (Client, Booking, Subscriber)
│   │   └── crud.py            # Оптимизированные запросы
│   ├── bot/
│   │   ├── handlers/          # Обработчики (admin, broadcast)
│   │   ├── keyboards/         # Inline-клавиатуры
│   │   ├── middleware/        # Rate limiting
│   │   └── scheduler.py       # Напоминания о бронях
│   └── webapp/
│       ├── app.py             # FastAPI + WebSocket
│       ├── templates/         # HTML шаблоны
│       └── static/            # CSS/JS (WebSocket client)
├── scripts/
│   ├── migrate_to_postgres.py # Миграция данных
│   ├── backup_db.py           # Автобэкапы
│   └── ...
└── Документация:
    ├── OPTIMIZATIONS_V3.md    # Подробное описание оптимизаций
    ├── UPGRADE_TO_V3.md       # Руководство по обновлению
    └── DEPLOY_*.md            # Инструкции по деплою
```

---

## 🛠️ Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка окружения

Создай `.env` на основе `.env.example`:

```env
# Telegram Bot
BOT_TOKEN=123456:replace-me

# Database (PostgreSQL для production)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/filin

# Web App URL
WEBAPP_URL=https://your-app.onrender.com/webapp

# Admin IDs
ADMIN_IDS=123456789,987654321

# PostgreSQL Pool (оптимизация)
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=5
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
```

### 3. Запуск

```bash
# Terminal 1: WebApp backend
python -m app.run_webapp

# Terminal 2: Telegram bot
python main.py
```

Или одной командой в PowerShell:
```powershell
.\run_local.ps1
```

---

## 🚀 Деплой на Render

### 1. Создай PostgreSQL:

```
Render Dashboard → New → PostgreSQL
Database: filin-db
Plan: Free (90 дней)
```

### 2. Скопируй Internal Database URL и преобразуй:

```env
DATABASE_URL=postgresql+asyncpg://user:password@ep-xxx.aws.neon.tech:5432/filin
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=2
```

### 3. Добавь переменные в Render Dashboard:

```env
BOT_TOKEN=...
DATABASE_URL=postgresql+asyncpg://...
WEBAPP_URL=https://your-app.onrender.com/webapp
ADMIN_IDS=...
DB_POOL_SIZE=5
```

### 4. Deploy!

Render автоматически:
- ✅ Установит зависимости
- ✅ Создаст таблицы БД
- ✅ Запустит FastAPI + бот
- ✅ Настроит HTTPS

---

## 📱 Админ-команды

| Команда | Описание |
|---------|----------|
| `/admin` | Список админ-команд |
| `/dashboard` | Дашборд администратора |
| `/broadcast` | **Рассылка подписчикам** |
| `/subscribers` | **Статистика подписчиков** |
| `/check_client [id]` | Информация о клиенте |
| `/add_visits [id] [кол-во]` | Добавить визиты |
| `/reset_visits [id]` | Сбросить визиты |
| `/set_schedule [текст]` | Обновить график |
| `/set_contacts [текст]` | Обновить контакты |
| `/add_promo [заголовок] | [описание] | [url]` | Добавить акцию |

---

## 🔧 Миграция на PostgreSQL

### Автоматическая миграция:

```bash
python scripts/migrate_to_postgres.py "postgresql+asyncpg://user:pass@host:5432/filin"
```

### Вручную:

1. Создай PostgreSQL базу
2. Обнови `DATABASE_URL` в `.env`
3. Таблицы создадутся автоматически при старте

---

## 📊 API Endpoints

### Клиентские:
- `GET /webapp` - главная страница Mini App
- `GET /api/bootstrap` - данные для инициализации
- `POST /api/bookings` - создание брони
- `POST /api/bookings/{id}/cancel` - отмена брони
- `GET /api/availability` - доступность столов

### Админские:
- `GET /api/admin/stats` - статистика за сегодня
- `GET /api/admin/tables` - карта столов
- `GET /api/admin/bookings` - список броней
- `POST /api/admin/bookings/{id}/status` - изменение статуса
- `GET /api/admin/broadcast/subscribers` - количество подписчиков
- `POST /api/admin/broadcast` - **отправка рассылки**
- `WebSocket /ws/admin` - **синхронизация в реальном времени**

---

## 🎯 Производительность

| Метрика | SQLite | PostgreSQL v3.0 |
|---------|--------|-----------------|
| Время ответа API | ~200ms | ~50ms |
| Одновременных подключений | 1-5 | 50+ |
| Надежность хранения | ⚠️ Файл | ✅ ACID |
| Синхронизация админки | Polling 5s | WebSocket |
| Рассылки | ❌ Нет | ✅ До 1000/мин |

---

## 📚 Документация

- **[OPTIMIZATIONS_V3.md](OPTIMIZATIONS_V3.md)** - подробное описание оптимизаций
- **[UPGRADE_TO_V3.md](UPGRADE_TO_V3.md)** - руководство по обновлению
- **[DEPLOY_RAILWAY.md](DEPLOY_RAILWAY.md)** - деплой на Railway
- **[DEPLOY_RENDER.md](DEPLOY_RENDER.md)** - деплой на Render
- **[DEPLOY_WEB.md](DEPLOY_WEB.md)** - деплой на Yandex Cloud

---

## ⚠️ Важные замечания

1. **SQLite vs PostgreSQL**: SQLite подходит для локальной разработки, для production используй PostgreSQL
2. **WebSocket**: Требует HTTPS в production (Render/Railway предоставляют автоматически)
3. **Рассылки**: Соблюдай лимиты Telegram (30 сообщений/сек)
4. **Connection Pool**: Настрой `DB_POOL_SIZE` в зависимости от тарифа (5 для free, 10+ для paid)

---

## 🆘 Поддержка

### Частые проблемы:

| Проблема | Решение |
|----------|---------|
| "no module named 'asyncpg'" | `pip install asyncpg` |
| Ошибка БД | Проверь `DATABASE_URL` формат |
| Рассылка не работает | Проверь `/subscribers`, BOT_TOKEN |
| Бот не отвечает | Проверь логи: Render Dashboard → Logs |

### Логи:

```bash
# WebApp
tail -f logs.txt

# PostgreSQL (Render)
Dashboard → Logs
```

---

## 📈 Roadmap

- [ ] Redis для кэширования
- [ ] Alembic миграции
- [ ] Экспорт статистики в CSV
- [ ] Push-уведомления
- [ ] Интеграция с 2GIS для отзывов

---

## 📝 License

MIT

---

**Готово к production! 🦉**

Для вопросов: @your_contact
