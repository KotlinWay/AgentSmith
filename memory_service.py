"""
Сервис внешней памяти для агента (День 9)
Хранит долговременную память в SQLite
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import os


class MemoryService:
    """Сервис для работы с внешней памятью агента"""

    def __init__(self, db_path: str = "agent_memory.db"):
        """
        Инициализация сервиса памяти

        Args:
            db_path: путь к файлу базы данных SQLite
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Создание таблиц базы данных если их нет"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Таблица сессий диалогов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)

        # Таблица сообщений в диалогах
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tokens INTEGER DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)

        # Таблица долговременных заметок/фактов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                importance INTEGER DEFAULT 5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                metadata TEXT
            )
        """)

        # Таблица промежуточных результатов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id),
                UNIQUE(session_id, key)
            )
        """)

        # Индексы для быстрого поиска
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_context_session ON context(session_id)")

        conn.commit()
        conn.close()

    # ==================== УПРАВЛЕНИЕ СЕССИЯМИ ====================

    def create_session(self, session_id: str, title: str = None, metadata: Dict = None) -> bool:
        """
        Создать новую сессию диалога

        Args:
            session_id: уникальный ID сессии
            title: название сессии
            metadata: дополнительные метаданные

        Returns:
            True если создано успешно
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            metadata_json = json.dumps(metadata) if metadata else None

            cursor.execute("""
                INSERT INTO sessions (session_id, title, metadata)
                VALUES (?, ?, ?)
            """, (session_id, title or f"Сессия {session_id}", metadata_json))

            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            # Сессия уже существует
            return False

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Получить информацию о сессии"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM sessions WHERE session_id = ?
        """, (session_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'id': row['id'],
                'session_id': row['session_id'],
                'title': row['title'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'metadata': json.loads(row['metadata']) if row['metadata'] else None
            }
        return None

    def list_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получить список всех сессий"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM sessions
            ORDER BY updated_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [{
            'id': row['id'],
            'session_id': row['session_id'],
            'title': row['title'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'metadata': json.loads(row['metadata']) if row['metadata'] else None
        } for row in rows]

    def delete_session(self, session_id: str) -> bool:
        """Удалить сессию и все связанные данные"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Удаляем связанные сообщения и контекст
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM context WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

        conn.commit()
        affected = cursor.rowcount
        conn.close()

        return affected > 0

    # ==================== УПРАВЛЕНИЕ СООБЩЕНИЯМИ ====================

    def save_message(self, session_id: str, role: str, content: str, tokens: int = 0) -> bool:
        """
        Сохранить сообщение в историю

        Args:
            session_id: ID сессии
            role: роль (user/assistant/system)
            content: содержимое сообщения
            tokens: количество токенов

        Returns:
            True если сохранено успешно
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Сохраняем сообщение
            cursor.execute("""
                INSERT INTO messages (session_id, role, content, tokens)
                VALUES (?, ?, ?, ?)
            """, (session_id, role, content, tokens))

            # Обновляем время последнего обновления сессии
            cursor.execute("""
                UPDATE sessions
                SET updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
            """, (session_id,))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Ошибка сохранения сообщения: {e}")
            return False

    def get_messages(self, session_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        Получить историю сообщений сессии

        Args:
            session_id: ID сессии
            limit: максимальное количество последних сообщений

        Returns:
            Список сообщений
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if limit:
            cursor.execute("""
                SELECT * FROM messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
            """, (session_id, limit))
        else:
            cursor.execute("""
                SELECT * FROM messages
                WHERE session_id = ?
                ORDER BY id ASC
            """, (session_id,))

        rows = cursor.fetchall()
        conn.close()

        messages = [{
            'id': row['id'],
            'role': row['role'],
            'content': row['content'],
            'timestamp': row['timestamp'],
            'tokens': row['tokens']
        } for row in rows]

        # Если был лимит, переворачиваем порядок обратно (от старых к новым)
        if limit:
            messages.reverse()

        return messages

    def get_message_count(self, session_id: str) -> int:
        """Получить количество сообщений в сессии"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM messages WHERE session_id = ?
        """, (session_id,))

        count = cursor.fetchone()[0]
        conn.close()

        return count

    # ==================== УПРАВЛЕНИЕ ДОЛГОВРЕМЕННОЙ ПАМЯТЬЮ ====================

    def save_memory(self, key: str, value: Any, category: str = 'general',
                   importance: int = 5, metadata: Dict = None) -> bool:
        """
        Сохранить факт в долговременную память

        Args:
            key: ключ (уникальный идентификатор факта)
            value: значение (может быть строка, число, dict, list)
            category: категория (для организации памяти)
            importance: важность от 1 до 10
            metadata: дополнительные метаданные

        Returns:
            True если сохранено успешно
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Преобразуем value в JSON если это не строка
            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)

            metadata_json = json.dumps(metadata) if metadata else None

            # Пытаемся обновить существующую запись или создать новую
            cursor.execute("""
                INSERT INTO memories (key, value, category, importance, metadata)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    category = excluded.category,
                    importance = excluded.importance,
                    metadata = excluded.metadata,
                    updated_at = CURRENT_TIMESTAMP
            """, (key, value, category, importance, metadata_json))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Ошибка сохранения памяти: {e}")
            return False

    def get_memory(self, key: str) -> Optional[Any]:
        """
        Получить значение из долговременной памяти

        Args:
            key: ключ

        Returns:
            Значение или None если не найдено
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE memories
            SET access_count = access_count + 1
            WHERE key = ?
        """, (key,))

        cursor.execute("""
            SELECT value FROM memories WHERE key = ?
        """, (key,))

        row = cursor.fetchone()
        conn.commit()
        conn.close()

        if row:
            value = row[0]
            # Пытаемся распарсить JSON
            try:
                return json.loads(value)
            except:
                return value
        return None

    def get_memories_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Получить все записи памяти по категории"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM memories
            WHERE category = ?
            ORDER BY importance DESC, updated_at DESC
        """, (category,))

        rows = cursor.fetchall()
        conn.close()

        return [{
            'key': row['key'],
            'value': json.loads(row['value']) if row['value'].startswith('{') or row['value'].startswith('[') else row['value'],
            'category': row['category'],
            'importance': row['importance'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'access_count': row['access_count']
        } for row in rows]

    def list_all_memories(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Получить все записи памяти"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM memories
            ORDER BY importance DESC, updated_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [{
            'key': row['key'],
            'value': json.loads(row['value']) if row['value'].startswith('{') or row['value'].startswith('[') else row['value'],
            'category': row['category'],
            'importance': row['importance'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'access_count': row['access_count']
        } for row in rows]

    def delete_memory(self, key: str) -> bool:
        """Удалить запись из памяти"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM memories WHERE key = ?", (key,))

        conn.commit()
        affected = cursor.rowcount
        conn.close()

        return affected > 0

    # ==================== УПРАВЛЕНИЕ КОНТЕКСТОМ ====================

    def save_context(self, session_id: str, key: str, value: Any) -> bool:
        """
        Сохранить промежуточный результат в контекст сессии

        Args:
            session_id: ID сессии
            key: ключ
            value: значение

        Returns:
            True если сохранено успешно
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Преобразуем value в JSON если это не строка
            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)

            cursor.execute("""
                INSERT INTO context (session_id, key, value)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id, key) DO UPDATE SET
                    value = excluded.value,
                    created_at = CURRENT_TIMESTAMP
            """, (session_id, key, value))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Ошибка сохранения контекста: {e}")
            return False

    def get_context(self, session_id: str, key: str) -> Optional[Any]:
        """Получить значение из контекста сессии"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT value FROM context
            WHERE session_id = ? AND key = ?
        """, (session_id, key))

        row = cursor.fetchone()
        conn.close()

        if row:
            value = row[0]
            # Пытаемся распарсить JSON
            try:
                return json.loads(value)
            except:
                return value
        return None

    def get_all_context(self, session_id: str) -> Dict[str, Any]:
        """Получить весь контекст сессии"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT key, value FROM context WHERE session_id = ?
        """, (session_id,))

        rows = cursor.fetchall()
        conn.close()

        context = {}
        for row in rows:
            key = row['key']
            value = row['value']
            # Пытаемся распарсить JSON
            try:
                context[key] = json.loads(value)
            except:
                context[key] = value

        return context

    def delete_context(self, session_id: str, key: str = None) -> bool:
        """
        Удалить контекст сессии

        Args:
            session_id: ID сессии
            key: конкретный ключ (если None - удаляется весь контекст сессии)

        Returns:
            True если удалено успешно
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if key:
            cursor.execute("DELETE FROM context WHERE session_id = ? AND key = ?", (session_id, key))
        else:
            cursor.execute("DELETE FROM context WHERE session_id = ?", (session_id,))

        conn.commit()
        affected = cursor.rowcount
        conn.close()

        return affected > 0

    # ==================== УТИЛИТЫ ====================

    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику использования памяти"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Количество сессий
        cursor.execute("SELECT COUNT(*) FROM sessions")
        sessions_count = cursor.fetchone()[0]

        # Количество сообщений
        cursor.execute("SELECT COUNT(*) FROM messages")
        messages_count = cursor.fetchone()[0]

        # Количество записей в памяти
        cursor.execute("SELECT COUNT(*) FROM memories")
        memories_count = cursor.fetchone()[0]

        # Количество записей в контексте
        cursor.execute("SELECT COUNT(*) FROM context")
        context_count = cursor.fetchone()[0]

        # Размер файла БД
        db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

        conn.close()

        return {
            'sessions': sessions_count,
            'messages': messages_count,
            'memories': memories_count,
            'context_entries': context_count,
            'db_size_bytes': db_size,
            'db_size_mb': round(db_size / (1024 * 1024), 2)
        }

    def clear_all(self, confirm: bool = False) -> bool:
        """
        ОПАСНО: Очистить всю базу данных

        Args:
            confirm: должно быть True для подтверждения

        Returns:
            True если очищено
        """
        if not confirm:
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM context")
        cursor.execute("DELETE FROM messages")
        cursor.execute("DELETE FROM memories")
        cursor.execute("DELETE FROM sessions")

        conn.commit()
        conn.close()

        return True
