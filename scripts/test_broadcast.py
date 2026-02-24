#!/usr/bin/env python3
"""
Тест рассылки подписчикам.
Отправляет тестовое сообщение всем активным подписчикам.
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем проект в path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.db.base import session_factory
from app.db import crud
from aiogram import Bot


async def test_broadcast():
    """Отправить тестовую рассылку."""
    settings = get_settings()
    
    if not settings.bot_token or settings.bot_token == "123456:replace-me":
        print("❌ BOT_TOKEN не настроен!")
        return False
    
    bot = Bot(token=settings.bot_token)
    
    async with session_factory() as session:
        # Получаем подписчиков
        subscribers = await crud.get_active_subscribers(session)
        count = len(subscribers)
        
        if count == 0:
            print("❌ Нет активных подписчиков")
            print("   Подписчики создаются автоматически при /start")
            await bot.session.close()
            return False
        
        print(f"📊 Найдено подписчиков: {count}")
        print()
        
        # Спрашиваем подтверждение
        response = input("📤 Отправить тестовую рассылку? (y/n): ")
        if response.lower() != 'y':
            print("❌ Отменено")
            await bot.session.close()
            return False
        
        success = 0
        failed = 0
        
        print()
        for sub in subscribers:
            try:
                await bot.send_message(
                    chat_id=sub.telegram_id,
                    text="🧪 <b>Тестовая рассылка</b>\n\n"
                         "Это тестовое сообщение для проверки функционала рассылки.\n\n"
                         "✅ Если вы видите это сообщение - рассылка работает!",
                    parse_mode="HTML"
                )
                await crud.update_last_mailed(session, sub.telegram_id)
                success += 1
                print(f"✅ Отправлено: {sub.telegram_id}")
            except Exception as e:
                failed += 1
                print(f"❌ Ошибка ({sub.telegram_id}): {e}")
            
            # Anti-flood
            await asyncio.sleep(0.05)
        
        await bot.session.close()
        
        print()
        print("=" * 50)
        print(f"✅ Успешно: {success}")
        print(f"❌ Ошибок: {failed}")
        print(f"📊 Всего: {count}")
        print("=" * 50)
        
        return failed == 0


def main():
    print("=" * 50)
    print("📢 Тест рассылки")
    print("=" * 50)
    print()
    
    result = asyncio.run(test_broadcast())
    
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
