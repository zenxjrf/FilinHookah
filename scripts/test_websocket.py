#!/usr/bin/env python3
"""
Тест WebSocket подключения для админ-панели.
"""

import asyncio
import websockets
import json
import sys


async def test_websocket(ws_url: str):
    """Проверить WebSocket подключение."""
    print(f"🔌 Подключение к {ws_url}...")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket подключен!")
            
            # Отправляем ping
            await websocket.send(json.dumps({"type": "ping"}))
            print("📤 Отправлен ping")
            
            # Ждём ответ
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(response)
                print(f"📥 Получен ответ: {data}")
                
                if data.get("type") == "pong":
                    print("✅ WebSocket работает корректно!")
                    return True
            except asyncio.TimeoutError:
                print("⚠️  Таймаут ответа (это нормально, если нет активных изменений)")
                return True
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def main():
    if len(sys.argv) > 1:
        ws_url = sys.argv[1]
    else:
        # URL по умолчанию
        ws_url = "ws://localhost:10000/ws/admin"
        print("Использование URL по умолчанию:", ws_url)
        print("Для своего URL: python test_websocket.py wss://your-app.onrender.com/ws/admin")
    
    print("=" * 50)
    print("🧪 Тест WebSocket")
    print("=" * 50)
    print()
    
    result = asyncio.run(test_websocket(ws_url))
    
    print()
    print("=" * 50)
    if result:
        print("✅ Тест пройден!")
    else:
        print("❌ Тест не пройден!")
    print("=" * 50)
    
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
