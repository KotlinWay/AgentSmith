#!/usr/bin/env python3
"""
GitHub MCP Service - сервис для работы с GitHub MCP сервером.
День 10: Интеграция с GitHub через MCP
"""

import asyncio
import os
from typing import Any, Dict, List
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class GitHubMCPService:
    """
    Сервис для работы с GitHub MCP сервером из синхронного кода.
    Подключается к GitHub MCP серверу через npx.
    """

    def __init__(self, github_token: str):
        """
        Args:
            github_token: GitHub Personal Access Token
        """
        self.github_token = github_token

        # Параметры для запуска GitHub MCP сервера через npx
        self.server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={
                "GITHUB_PERSONAL_ACCESS_TOKEN": github_token,
                "PATH": os.environ.get("PATH", "")
            }
        )

    async def _get_tools_async(self) -> List[Dict[str, Any]]:
        """
        Асинхронно получает список инструментов от GitHub MCP сервера.
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
        Асинхронно вызывает инструмент GitHub MCP сервера.

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
            raise Exception(f"Ошибка получения инструментов GitHub MCP: {str(e)}")

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
