#!/usr/bin/env python3
"""
Простой MCP сервер с набором инструментов.
День 10: Подключение MCP
"""

import asyncio
import json
from typing import Any
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp import ServerSession
import mcp.server.stdio


# Создаем сервер
server = Server("demo-mcp-server")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """
    Возвращает список доступных инструментов MCP сервера.
    """
    return [
        Tool(
            name="calculator",
            description="Выполняет базовые математические операции",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["add", "subtract", "multiply", "divide"],
                        "description": "Математическая операция"
                    },
                    "a": {
                        "type": "number",
                        "description": "Первое число"
                    },
                    "b": {
                        "type": "number",
                        "description": "Второе число"
                    }
                },
                "required": ["operation", "a", "b"]
            }
        ),
        Tool(
            name="get_current_time",
            description="Возвращает текущее время",
            inputSchema={
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "Временная зона (опционально)",
                        "default": "UTC"
                    }
                }
            }
        ),
        Tool(
            name="text_analyzer",
            description="Анализирует текст и возвращает статистику",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Текст для анализа"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["words", "chars", "lines", "all"],
                        "description": "Режим анализа",
                        "default": "all"
                    }
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="json_formatter",
            description="Форматирует JSON с указанными отступами",
            inputSchema={
                "type": "object",
                "properties": {
                    "json_string": {
                        "type": "string",
                        "description": "JSON строка для форматирования"
                    },
                    "indent": {
                        "type": "integer",
                        "description": "Количество пробелов для отступа",
                        "default": 2
                    }
                },
                "required": ["json_string"]
            }
        ),
        Tool(
            name="weather_info",
            description="Получает информацию о погоде (демо версия)",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Название города"
                    },
                    "units": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Единицы измерения температуры",
                        "default": "celsius"
                    }
                },
                "required": ["city"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """
    Обработчик вызовов инструментов.
    """
    from datetime import datetime

    if name == "calculator":
        operation = arguments.get("operation")
        a = arguments.get("a")
        b = arguments.get("b")

        result = None
        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            if b == 0:
                return [TextContent(type="text", text="Ошибка: деление на ноль")]
            result = a / b

        return [TextContent(
            type="text",
            text=f"Результат: {a} {operation} {b} = {result}"
        )]

    elif name == "get_current_time":
        timezone = arguments.get("timezone", "UTC")
        current_time = datetime.now().isoformat()
        return [TextContent(
            type="text",
            text=f"Текущее время ({timezone}): {current_time}"
        )]

    elif name == "text_analyzer":
        text = arguments.get("text", "")
        mode = arguments.get("mode", "all")

        words = len(text.split())
        chars = len(text)
        lines = len(text.split('\n'))

        stats = {}
        if mode in ["words", "all"]:
            stats["words"] = words
        if mode in ["chars", "all"]:
            stats["chars"] = chars
        if mode in ["lines", "all"]:
            stats["lines"] = lines

        return [TextContent(
            type="text",
            text=f"Статистика текста: {json.dumps(stats, ensure_ascii=False, indent=2)}"
        )]

    elif name == "json_formatter":
        json_string = arguments.get("json_string", "")
        indent = arguments.get("indent", 2)

        try:
            parsed = json.loads(json_string)
            formatted = json.dumps(parsed, ensure_ascii=False, indent=indent)
            return [TextContent(
                type="text",
                text=f"Отформатированный JSON:\n{formatted}"
            )]
        except json.JSONDecodeError as e:
            return [TextContent(
                type="text",
                text=f"Ошибка парсинга JSON: {str(e)}"
            )]

    elif name == "weather_info":
        city = arguments.get("city")
        units = arguments.get("units", "celsius")

        # Демо данные
        demo_weather = {
            "city": city,
            "temperature": 22 if units == "celsius" else 72,
            "units": units,
            "condition": "Солнечно",
            "humidity": "65%",
            "wind": "10 км/ч"
        }

        return [TextContent(
            type="text",
            text=f"Погода в {city}:\n{json.dumps(demo_weather, ensure_ascii=False, indent=2)}"
        )]

    else:
        return [TextContent(
            type="text",
            text=f"Неизвестный инструмент: {name}"
        )]


async def main():
    """Запуск MCP сервера через stdio"""
    import sys
    # Печатаем в stderr, чтобы не мешать JSONRPC коммуникации через stdout
    print("🚀 Запуск MCP сервера...", file=sys.stderr, flush=True)

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
