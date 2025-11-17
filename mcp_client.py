#!/usr/bin/env python3
"""
MCP Клиент для подключения к MCP серверу и получения списка инструментов.
День 10: Подключение MCP
"""

import asyncio
import json
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def connect_to_mcp_server():
    """
    Подключается к MCP серверу и получает список доступных инструментов.
    """
    # Параметры для запуска сервера через stdio
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
        env=None
    )

    async with AsyncExitStack() as stack:
        # Подключаемся к серверу
        print("📡 Подключение к MCP серверу...")
        stdio_transport = await stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        session = await stack.enter_async_context(ClientSession(stdio, write))

        # Инициализация соединения
        print("🔧 Инициализация MCP соединения...")
        await session.initialize()

        print("\n✅ Соединение установлено успешно!\n")

        # Получаем список инструментов
        print("🔍 Запрашиваем список доступных инструментов...\n")
        tools_list = await session.list_tools()

        # Выводим информацию о каждом инструменте
        print("=" * 70)
        print(f"📋 СПИСОК ДОСТУПНЫХ ИНСТРУМЕНТОВ MCP ({len(tools_list.tools)} шт.)")
        print("=" * 70)
        print()

        for idx, tool in enumerate(tools_list.tools, 1):
            print(f"[{idx}] {tool.name}")
            print(f"    Описание: {tool.description}")
            print(f"    Схема входных данных:")

            # Красиво форматируем схему
            schema_str = json.dumps(tool.inputSchema, ensure_ascii=False, indent=6)
            for line in schema_str.split('\n'):
                print(f"    {line}")
            print()

        print("=" * 70)
        print(f"\n✨ Всего найдено инструментов: {len(tools_list.tools)}")

        # Демонстрация вызова одного из инструментов
        print("\n" + "=" * 70)
        print("🧪 ТЕСТИРОВАНИЕ ИНСТРУМЕНТА: calculator")
        print("=" * 70)

        # Вызываем калькулятор
        result = await session.call_tool(
            name="calculator",
            arguments={
                "operation": "add",
                "a": 15,
                "b": 27
            }
        )

        print(f"\n📊 Результат вызова:")
        for content in result.content:
            print(f"   {content.text}")

        print("\n" + "=" * 70)
        print("🧪 ТЕСТИРОВАНИЕ ИНСТРУМЕНТА: text_analyzer")
        print("=" * 70)

        # Вызываем анализатор текста
        test_text = """Привет! Это тестовый текст для анализа.
Он содержит несколько строк.
И различные слова."""

        result = await session.call_tool(
            name="text_analyzer",
            arguments={
                "text": test_text,
                "mode": "all"
            }
        )

        print(f"\n📊 Результат вызова:")
        for content in result.content:
            print(f"   {content.text}")

        print("\n" + "=" * 70)
        print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
        print("=" * 70)

        return tools_list.tools


async def main():
    """Главная функция"""
    print("🎯 MCP Client - День 10 Челленджа\n")

    try:
        tools = await connect_to_mcp_server()
        print(f"\n🎉 Успешно получено {len(tools)} инструментов от MCP сервера!")
    except Exception as e:
        print(f"\n❌ Ошибка при подключении к MCP серверу:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
