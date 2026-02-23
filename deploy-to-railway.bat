@echo off
echo ========================================
echo   Filin Bot - Подготовка к Railway
echo ========================================
echo.

REM Проверка Git
where git >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Git не установлен!
    echo Установи Git: https://git-scm.com/download/win
    pause
    exit /b 1
)

echo [OK] Git установлен
echo.

REM Инициализация Git
echo [1/5] Инициализация Git...
git init
git add .
git commit -m "Filin Bot v2.0 - Optimized for Railway"

echo.
echo [2/5] Введи название репозитория (например: filin-bot):
set /p REPO_NAME=
echo.

REM Проверка GitHub CLI
where gh >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [3/5] Создание репозитория на GitHub...
    gh repo create %REPO_NAME% --public --source=. --remote=origin --push
    echo.
    echo [OK] Репозиторий создан!
) else (
    echo [3/5] GitHub CLI не установлен...
    echo.
    echo Сделай вручную:
    echo   1. Зайди на https://github.com/new
    echo   2. Название репозитория: %REPO_NAME%
    echo   3. Нажми "Create repository"
    echo   4. Выполни команды ниже:
    echo.
    echo   git remote add origin https://github.com/ТВОЙ_USERNAME/%REPO_NAME%.git
    echo   git branch -M main
    echo   git push -u origin main
    echo.
)

echo.
echo [4/5] Создание .env для Railway...
echo.
echo Скопируй эти переменные в Railway Dashboard:
echo.
echo BOT_TOKEN=8306362120:AAHXCXOXFk_Eam6gbfnwK0f0vTyI16RNFZo
echo DATABASE_URL=sqlite+aiosqlite:///./filin.db
echo WEBAPP_URL=https://%REPO_NAME%.railway.app
echo ADMIN_IDS=1698158035,987654321
echo WORKERS_CHAT_ID=-1003748695791
echo LOG_PATH=logs.txt
echo DEFAULT_SCHEDULE=Ежедневно с 14:00 до 2:00
echo DEFAULT_CONTACTS=Phone: +7 ^(+7 (000) 000-00-00^nAddress: Example street, 1
echo.
echo [5/5] Следующие шаги:
echo.
echo   1. Зайди на https://railway.app
echo   2. Нажми "New Project"
echo   3. Выбери "Deploy from GitHub repo"
echo   4. Выбери репозиторий: %REPO_NAME%
echo   5. Добавь переменные окружения (см. выше)
echo.
echo ========================================
echo   Готово!
echo ========================================
echo.
pause
