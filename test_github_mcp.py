#!/usr/bin/env python3
"""
Тестовый скрипт для проверки подключения к GitHub MCP серверу.
"""

import sys
import os
sys.path.insert(0, '/home/user/AgentSmith')

from github_mcp_service import GitHubMCPService

# Получаем токен из переменной окружения
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
if not GITHUB_TOKEN:
    print("❌ Ошибка: GITHUB_TOKEN не установлен")
    print("Установите переменную окружения:")
    print("  export GITHUB_TOKEN=your_token_here")
    sys.exit(1)

def test_github_mcp():
    """Тестируем подключение к GitHub MCP"""
    print("🎯 Тестирование GitHub MCP Service\n")
    print("=" * 70)

    try:
        # Создаем сервис
        print("1️⃣ Создание GitHub MCP Service...")
        service = GitHubMCPService(GITHUB_TOKEN)
        print("✅ Сервис создан\n")

        # Получаем список инструментов
        print("2️⃣ Получение списка инструментов...")
        tools = service.get_tools()
        print(f"✅ Получено {len(tools)} инструментов\n")

        # Выводим список инструментов
        print("=" * 70)
        print(f"📋 СПИСОК ИНСТРУМЕНТОВ GITHUB MCP ({len(tools)} шт.)")
        print("=" * 70)
        print()

        for idx, tool in enumerate(tools, 1):
            print(f"[{idx}] {tool['name']}")
            print(f"    Описание: {tool['description'][:80]}...")
            params = tool.get('inputSchema', {}).get('properties', {})
            print(f"    Параметров: {len(params)}")
            print()

        print("=" * 70)
        print(f"✨ Всего найдено инструментов: {len(tools)}")
        print("=" * 70)
        print("\n🎉 Тест успешно завершен!")

    except Exception as e:
        print(f"\n❌ Ошибка при тестировании:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    success = test_github_mcp()
    sys.exit(0 if success else 1)
