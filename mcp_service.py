#!/usr/bin/env python3
"""
MCP Service - обертка для работы с MCP из синхронного Flask приложения.
День 10: Интеграция MCP в веб-интерфейс
"""

import asyncio
from typing import Any, Dict, List
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPService:
    """
    Сервис для работы с MCP сервером из синхронного кода.
    Предоставляет синхронные методы для асинхронных операций MCP.
    """

    def __init__(self, server_script: str = "mcp_server.py"):
        """
        Args:
            server_script: путь к скрипту MCP сервера
        """
        self.server_script = server_script
        self.server_params = StdioServerParameters(
            command="python",
            args=[server_script],
            env=None
        )

    async def _get_tools_async(self) -> List[Dict[str, Any]]:
        """
        Асинхронно получает список инструментов от MCP сервера.
        """
        async with AsyncExitStack() as stack:
            # Подключаемся к серверу
            stdio_transport = await stack.enter_async_context(
                stdio_client(self.server_params)
            )
            stdio, write = stdio_transport
            session = await stack.enter_async_context(ClientSession(stdio, write))

            # Инициализация
            await session.initialize()

            # Получаем список инструментов
            tools_list = await session.list_tools()

            # Преобразуем в словари для JSON
            tools = []
            for tool in tools_list.tools:
                tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                })

            return tools

    async def _call_tool_async(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Асинхронно вызывает инструмент MCP сервера.

        Args:
            tool_name: название инструмента
            arguments: аргументы для инструмента

        Returns:
            Результат выполнения инструмента
        """
        async with AsyncExitStack() as stack:
            # Подключаемся к серверу
            stdio_transport = await stack.enter_async_context(
                stdio_client(self.server_params)
            )
            stdio, write = stdio_transport
            session = await stack.enter_async_context(ClientSession(stdio, write))

            # Инициализация
            await session.initialize()

            # Вызываем инструмент
            result = await session.call_tool(name=tool_name, arguments=arguments)

            # Формируем ответ
            response = {
                "success": True,
                "tool": tool_name,
                "arguments": arguments,
                "content": []
            }

            for content in result.content:
                response["content"].append({
                    "type": content.type,
                    "text": content.text
                })

            return response

    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Синхронная обертка для получения списка инструментов.

        Returns:
            Список инструментов
        """
        try:
            # Создаем новый event loop для асинхронной операции
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self._get_tools_async())
                return result
            finally:
                loop.close()
        except Exception as e:
            raise Exception(f"Ошибка получения инструментов: {str(e)}")

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Синхронная обертка для вызова инструмента.

        Args:
            tool_name: название инструмента
            arguments: аргументы для инструмента

        Returns:
            Результат выполнения
        """
        try:
            # Создаем новый event loop для асинхронной операции
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    self._call_tool_async(tool_name, arguments)
                )
                return result
            finally:
                loop.close()
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name,
                "arguments": arguments
            }


# Создаем глобальный экземпляр сервиса
mcp_service = MCPService()
