# Filin Telegram Bot + Mini App

MVP-проект Telegram-бота для кальянного заведения на `aiogram 3` с мини-приложением на `FastAPI`.

## Что реализовано
- Клиентское меню: акции, график, контакты, бронирование, мои брони, лояльность, отзывы.
- Бронирование через Telegram WebApp + обработка `web_app_data`.
- Админ-команды: `/admin`, `/bookings`, `/confirm_booking`, `/set_schedule`, `/set_contacts`, `/add_promo`.
- SQLite через SQLAlchemy (асинхронно), готово к миграции на PostgreSQL.
- Планировщик напоминаний за 1 час до брони (APScheduler).
- Базовый anti-flood middleware.

## Структура
- `main.py` - запуск бота (polling).
- `app/run_webapp.py` - запуск WebApp backend.
- `app/db/` - модели и CRUD.
- `app/bot/` - handlers, keyboards, middleware, scheduler.
- `app/webapp/` - FastAPI, HTML/CSS/JS мини-приложения.

## Запуск в PyCharm
1. Создайте/выберите `venv` в PyCharm.
2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
3. Создайте `.env` на основе `.env.example`.
4. Запустите backend мини-приложения:
   ```bash
   python -m app.run_webapp
   ```
5. Запустите бота:
   ```bash
   python main.py
   ```

Или одной командой в PowerShell:
```powershell
.\run_local.ps1
```

## Автозапуск в Windows (Task Scheduler)
Установка:
```powershell
.\scripts\install_autostart.ps1
```
Примечание: если доступ к `Task Scheduler` запрещен политикой, скрипт автоматически установит автозапуск через пользовательскую папку `Startup`.

## Быстрая настройка HTTPS для Mini App
Одна команда (скачает cloudflared, поднимет туннель, пропишет `WEBAPP_URL`, перезапустит процессы):
```powershell
.\scripts\setup_https_webapp.ps1
```

Проверка статуса:
```powershell
.\scripts\status_autostart.ps1
```

Удаление:
```powershell
.\scripts\uninstall_autostart.ps1
```

## Важно
- `WEBAPP_URL` должен быть HTTPS-адресом опубликованного WebApp в продакшене.
- Для PostgreSQL обновите `DATABASE_URL`, например:
  `postgresql+asyncpg://user:password@host:5432/filin`
- Перед продом рекомендуется добавить Alembic-миграции и полноценную верификацию `initData`.

## Быстрые сценарии
- Пользователь: `/start` -> кнопка `Забронировать` -> отправка данных из WebApp.
- Админ: `/admin` -> список команд.
