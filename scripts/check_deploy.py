#!/usr/bin/env python3
"""
Proverka gotovnosti proekta k deploy na Render.
"""

import sys
import os
from pathlib import Path

# Dobavlyaem proekt v path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

def check_env():
    """Proverit nalichie i korrektnost .env faila."""
    env_path = Path(".env")
    if not env_path.exists():
        print("[X] .env fail ne nayden!")
        print("    Sozdayte .env na osnove .env.example")
        return False
    
    required_vars = [
        "BOT_TOKEN",
        "DATABASE_URL",
        "WEBAPP_URL",
        "ADMIN_IDS"
    ]
    
    env_content = env_path.read_text(encoding="utf-8")
    missing = []
    
    for var in required_vars:
        if var not in env_content:
            missing.append(var)
    
    if missing:
        print(f"[X] Otsutstvuyut peremennye v .env: {', '.join(missing)}")
        return False
    
    # Proverka DATABASE_URL
    if "postgresql+asyncpg://" not in env_content:
        print("[!] Rekomenduetsya ispolzovat PostgreSQL dlya production")
        print("    DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db")
    
    print("[OK] .env fail korrektne")
    return True


def check_dependencies():
    """Proverit ustanovlennye zavisimosti."""
    try:
        import aiogram
        import fastapi
        import sqlalchemy
        import asyncpg
        import uvicorn
        print("[OK] Vse zavisimosti ustanovleny")
        return True
    except ImportError as e:
        print(f"[X] Otsutstvuet zavisimost: {e}")
        print("    Vypolnite: pip install -r requirements.txt")
        return False


def check_database():
    """Proverit podklyuchenie k BD."""
    import asyncio
    from app.db.base import engine
    
    async def test():
        try:
            async with engine.begin() as conn:
                await conn.execute(sqlalchemy.text("SELECT 1"))
            return True
        except Exception as e:
            print(f"[X] Oshibka podklyucheniya k BD: {e}")
            return False
    
    import sqlalchemy
    result = asyncio.run(test())
    if result:
        print("[OK] Podklyuchenie k BD rabotaet")
    return result


def check_bot_token():
    """Proverit token bota."""
    from app.config import get_settings
    
    settings = get_settings()
    if not settings.bot_token or settings.bot_token == "123456:replace-me":
        print("[X] BOT_TOKEN ne nastroen!")
        print("    Poluchite token v @BotFather")
        return False
    
    if not settings.bot_token.startswith(str(settings.bot_token).split(":")[0]):
        print("[X] Neverny format BOT_TOKEN")
        return False
    
    print("[OK] BOT_TOKEN nastroen")
    return True


def check_files():
    """Proverit nalichie vsekh neobkhodimykh faylov."""
    required = [
        "main.py",
        "app/webapp/app.py",
        "app/db/models.py",
        "app/db/crud.py",
        "requirements.txt",
        ".env"
    ]
    
    missing = []
    for file in required:
        if not Path(file).exists():
            missing.append(file)
    
    if missing:
        print(f"[X] Otsutstvuyut fayly: {', '.join(missing)}")
        return False
    
    print("[OK] Vse fayly na meste")
    return True


def main():
    print("=" * 50)
    print("Check gotovnosti k deploy")
    print("=" * 50)
    print()
    
    checks = [
        ("Files", check_files),
        ("Dependencies", check_dependencies),
        ("BOT_TOKEN", check_bot_token),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\nProverka: {name}")
        print("-" * 30)
        try:
            result = check_func()
        except Exception as e:
            print(f"[X] Oshibka: {e}")
            result = False
        results.append(result)
        print()
    
    print("=" * 50)
    print("Itogi:")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"OK: {passed}/{total}")
    
    if passed == total:
        print("\nVse gotovo k deploy!")
        print("\nSleduyusie shagi:")
        print("   1. Deploy na Render/Railway")
        print("   2. Nastroi DATABASE_URL (PostgreSQL)")
        print("   3. Prover rabotu bota: /start")
        print("   4. Prover admin-panel: /admin")
        print("   5. Testirui WebSocket (izmeni status broni)")
        return 0
    else:
        print("\nIsprav oshibki pered deployem!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
