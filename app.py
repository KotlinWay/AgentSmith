from flask import Flask, render_template, request, jsonify
import requests
import json
import os
import re
import time
from typing import Dict, Any
from memory_service import MemoryService
import uuid
from datetime import datetime

app = Flask(__name__)

# Инициализация сервиса внешней памяти (День 9)
memory = MemoryService("agent_memory.db")

# Текущая сессия (по умолчанию создаем новую при запуске)
current_session_id = str(uuid.uuid4())

# Загрузка конфигурации
def load_config():
    if os.path.exists('config.json'):
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        raise FileNotFoundError("config.json не найден! Создай его на основе config.example.json")

config = load_config()

# История диалога
chat_history = []
recommendation_history = []
reasoning_history = []

# История диалога с компрессией (День 8)
compressed_chat_history = []


class DialogHistoryManager:
    """
    Менеджер истории диалога с механизмом компрессии.
    Автоматически создает summary каждые N сообщений.
    """
    def __init__(self, compression_threshold=10, use_compression=True):
        """
        Args:
            compression_threshold: Количество сообщений до компрессии
            use_compression: Включить/выключить механизм компрессии
        """
        self.messages = []  # Полная история сообщений
        self.compressed_messages = []  # Сжатая история (summary + недавние сообщения)
        self.compression_threshold = compression_threshold
        self.use_compression = use_compression
        self.compression_count = 0  # Количество выполненных компрессий
        self.total_tokens_saved = 0  # Общее количество сэкономленных токенов

    def add_message(self, role, text):
        """
        Добавить новое сообщение в историю.
        Возвращает True, если была выполнена компрессия, иначе False.
        """
        message = {"role": role, "text": text}
        self.messages.append(message)

        # Проверяем, нужно ли выполнить компрессию
        if self.use_compression and len(self.messages) >= self.compression_threshold:
            return self._compress_history()
        return False

    def _compress_history(self):
        """
        Выполняет компрессию истории диалога.
        Создает summary из старых сообщений и сохраняет только недавние.
        Возвращает True, если компрессия была выполнена успешно.
        """
        # Разделяем историю на две части:
        # 1. Старая часть для компрессии (все кроме последних 3 сообщений)
        # 2. Новая часть для сохранения (последние 3 сообщения)
        messages_to_compress = self.messages[:-3]
        recent_messages = self.messages[-3:]

        if len(messages_to_compress) < 2:
            return False  # Недостаточно сообщений для компрессии

        # Создаем summary из старых сообщений
        summary_text = self._create_summary(messages_to_compress)

        # Подсчет сэкономленных токенов
        original_tokens = sum(estimate_tokens(msg["text"]) for msg in messages_to_compress)
        summary_tokens = estimate_tokens(summary_text)
        tokens_saved = original_tokens - summary_tokens

        self.total_tokens_saved += tokens_saved
        self.compression_count += 1

        # Формируем новую сжатую историю
        system_message = f"""КОНТЕКСТ ПРЕДЫДУЩЕГО ДИАЛОГА: {summary_text}

═══════════════════════════════════════════════
КРИТИЧЕСКИ ВАЖНЫЕ ИНСТРУКЦИИ ДЛЯ ТЕБЯ:
═══════════════════════════════════════════════

1. ТЫ - АССИСТЕНТ, КОТОРЫЙ ОТВЕЧАЕТ НА ВОПРОСЫ
2. ТЫ НЕ ЗАДАЕШЬ ВОПРОСЫ ПОЛЬЗОВАТЕЛЮ
3. ТЫ НЕ ПРЕДЛАГАЕШЬ ТЕМЫ ДЛЯ ОБСУЖДЕНИЯ

Твоя ЕДИНСТВЕННАЯ задача: прочитать последний вопрос пользователя и дать на него ПРЯМОЙ ОТВЕТ.

Контекст выше - это ТОЛЬКО справочная информация. НЕ продолжай темы из контекста.
Отвечай ТОЛЬКО на НОВЫЙ вопрос пользователя.

═══════════════════════════════════════════════
ПРИМЕРЫ ПРАВИЛЬНОГО И НЕПРАВИЛЬНОГО ПОВЕДЕНИЯ:
═══════════════════════════════════════════════

❌❌❌ КАТЕГОРИЧЕСКИ НЕПРАВИЛЬНО:
"Какие технические задачи нужно решить?"
"Какие риски могут возникнуть при поиске финансирования?"
"Давайте обсудим риски миссии"
"Хотите узнать больше о..."
"Может быть стоит рассмотреть..."

✅✅✅ ПРАВИЛЬНО:
"Технические задачи включают..."
"Основные риски миссии: 1) ... 2) ... 3) ..."
"Шансы на успех зависят от..."

═══════════════════════════════════════════════

ЗАПОМНИ: Ты отвечаешь ФАКТАМИ и ИНФОРМАЦИЕЙ, а НЕ задаешь вопросы!"""

        # ВАЖНО: Сохраняем только system message в compressed_messages
        # Актуальные сообщения будут браться из self.messages в get_history_for_api()
        self.compressed_messages = [
            {"role": "system", "text": system_message}
        ]

        # Очищаем полную историю, оставляем только недавние сообщения
        self.messages = recent_messages.copy()
        return True

    def _create_summary(self, messages):
        """
        Создает краткое резюме из списка сообщений.
        Использует модель суммаризации Yandex Cloud.
        """
        # ВАЖНО: Формируем текст ТОЛЬКО из ответов ассистента, без вопросов пользователя
        assistant_responses = []
        for msg in messages:
            if msg['role'] == 'assistant':
                assistant_responses.append(msg['text'])

        # Объединяем все ответы ассистента
        responses_text = "\n\n".join(assistant_responses)

        # Используем специализированную модель для суммаризации
        url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {config['api_key']}"
        }

        payload = {
            "modelUri": f"gpt://{config['catalog_id']}/summarization/latest",
            "completionOptions": {
                "stream": False,
                "temperature": 0.05,  # Максимально детерминированный результат
                "maxTokens": 300
            },
            "messages": [
                {
                    "role": "user",
                    "text": f"""Создай краткую справку из следующей информации.

СТРОГИЕ ТРЕБОВАНИЯ:
1. Пиши ТОЛЬКО ФАКТЫ - что было сказано, какая информация была дана
2. Используй ТОЛЬКО утвердительные предложения (с точкой в конце)
3. ЗАПРЕЩЕНО использовать вопросительные знаки (?)
4. ЗАПРЕЩЕНО писать: "нужно", "следует", "необходимо", "давайте", "можно ли", "как", "какие", "почему"
5. НЕ предлагай темы для обсуждения
6. НЕ формулируй задачи или вопросы

ПРАВИЛЬНЫЕ примеры:
✅ "Обсуждалась структура вселенной, теория Большого взрыва и темная материя."
✅ "Были рассмотрены варианты колонизации Марса и Луны, названы технические требования."

НЕПРАВИЛЬНЫЕ примеры:
❌ "Какие планеты лучше колонизировать?"
❌ "Нужно обсудить риски миссии."
❌ "Следует рассмотреть финансирование."

Исходная информация:
{responses_text}

Твоя справка (2-3 предложения с точками, БЕЗ вопросов):"""
                }
            ]
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()

            if "result" in result and "alternatives" in result["result"]:
                summary = result["result"]["alternatives"][0]["message"]["text"].strip()

                # Очищаем summary от типичных вводных фраз
                unwanted_phrases = [
                    "Перечисли основные моменты предыдущего диалога.",
                    "Основные моменты:",
                    "Резюме:",
                    "Краткое резюме:",
                    "В диалоге обсуждались следующие темы:",
                    "Пользователь спросил",
                    "Обсуждались темы:",
                    "В предыдущем диалоге:",
                    "Факты из диалога:",
                ]

                for phrase in unwanted_phrases:
                    if summary.lower().startswith(phrase.lower()):
                        summary = summary[len(phrase):].strip()
                        # Удаляем начальные двоеточия и точки после удаления фразы
                        summary = summary.lstrip(':. ')

                # КРИТИЧЕСКИ ВАЖНО: Удаляем ВСЕ предложения с вопросами
                # Разбиваем на предложения и оставляем только утвердительные
                sentences = summary.split('.')
                filtered_sentences = []
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    # Удаляем предложения с вопросительными знаками
                    if '?' in sentence:
                        continue
                    # Удаляем предложения, начинающиеся с вопросительных слов
                    lower_sentence = sentence.lower()
                    question_words = ['как', 'какой', 'какая', 'какие', 'почему', 'зачем', 'где',
                                     'куда', 'когда', 'чем', 'кто', 'что', 'нужно ли', 'следует ли',
                                     'можно ли', 'стоит ли']
                    if any(lower_sentence.startswith(word) for word in question_words):
                        continue
                    # Удаляем предложения с модальными словами (предложения задач)
                    modal_words = ['нужно', 'следует', 'необходимо', 'стоит', 'давайте']
                    if any(word in lower_sentence for word in modal_words):
                        continue
                    filtered_sentences.append(sentence)

                # Собираем обратно
                summary = '. '.join(filtered_sentences)
                if summary and not summary.endswith('.'):
                    summary += '.'

                return summary
            else:
                # Фоллбэк: простое текстовое резюме
                return f"Обсуждалось {len(messages)} сообщений"

        except Exception as e:
            # В случае ошибки возвращаем простое резюме
            return f"Предыдущий диалог ({len(messages)} сообщений)"

    def get_history_for_api(self, use_compressed=None):
        """
        Получить историю для отправки в API.

        Args:
            use_compressed: Если True - вернуть сжатую, если False - полную
                           Если None - использовать настройку self.use_compression

        Returns:
            list: Список сообщений для API
        """
        should_use_compressed = use_compressed if use_compressed is not None else self.use_compression

        if should_use_compressed and self.compressed_messages:
            # ВАЖНО: Формируем актуальную историю с system message + все текущие сообщения
            # compressed_messages[0] - это system message с контекстом
            # self.messages - это актуальные последние сообщения
            return [self.compressed_messages[0]] + self.messages
        else:
            return self.messages

    def get_stats(self):
        """Получить статистику использования компрессии"""
        full_tokens = sum(estimate_tokens(msg["text"]) for msg in self.messages)

        # Если есть компрессия, считаем токены как: system message + актуальные сообщения
        if self.compressed_messages:
            compressed_tokens = sum(estimate_tokens(msg["text"]) for msg in self.compressed_messages) + full_tokens
        else:
            compressed_tokens = full_tokens

        return {
            "total_messages": len(self.messages),
            "compressed_messages": len(self.compressed_messages) + len(self.messages) if self.compressed_messages else 0,
            "compression_count": self.compression_count,
            "total_tokens_saved": self.total_tokens_saved,
            "current_full_tokens": full_tokens,
            "current_compressed_tokens": compressed_tokens,
            "compression_ratio": round((1 - compressed_tokens / full_tokens) * 100, 2) if full_tokens > 0 else 0
        }

    def clear(self):
        """Очистить всю историю"""
        self.messages = []
        self.compressed_messages = []
        self.compression_count = 0
        self.total_tokens_saved = 0


# Создаем менеджер истории с компрессией
dialog_manager = DialogHistoryManager(compression_threshold=10, use_compression=True)


RECOMMENDATION_AGENT_PROMPT = """
Ты умный агент-советник по фильмам. Твоя задача - помочь пользователю найти идеальный фильм через диалог.

ВАЖНО: Ты работаешь в трёх режимах:

РЕЖИМ 1 - СБОР ИНФОРМАЦИИ (обычный текст):
- Веди естественный, дружелюбный диалог с пользователем
- ОБЯЗАТЕЛЬНО узнай: возраст пользователя и его пол (это важно для подбора подходящего контента)
- Задавай вопросы о его предпочтениях, настроении, компании
- Интересуйся жанрами, которые он любит или не любит
- Узнай, в какой обстановке он будет смотреть фильм (один, с друзьями, с семьей, на романтическом свидании)
- Учитывай его текущее настроение
- Можешь задать любимые актеры, режиссеры, конкретные фильмы которые понравились
- НЕ торопись! Задавай столько вопросов, сколько нужно для ГЛУБОКОГО понимания вкусов пользователя
- Это может быть 5, 7 или даже 10 вопросов - главное качество информации

РЕЖИМ 2 - ПРЕДЛОЖЕНИЕ ФИЛЬМОВ ДЛЯ ВЫБОРА (только JSON):
- Когда собрал детальную информацию (возраст, пол, жанры, настроение, компания и другие предпочтения), предложи 16 разных фильмов
- Верни ТОЛЬКО валидный JSON со списком фильмов (без пояснений, текста до/после, БЕЗ обрамляющих кавычек)
- Структура JSON должна быть строго такой:
{
  "type": "movie_selection",
  "message": "Отлично! Теперь выбери 4 фильма из этого списка, которые тебе больше всего интересны:",
  "movies": [
    "Название фильма 1",
    "Название фильма 2",
    ...
    "Название фильма 16"
  ]
}
- Подбирай разнообразные фильмы разных жанров, но подходящие по возрасту и общим предпочтениям
- Фильмы должны быть известными и качественными

РЕЖИМ 3 - ФИНАЛЬНАЯ РЕКОМЕНДАЦИЯ (только JSON):
- После того как пользователь выберет 4 фильма, он напишет что-то вроде "Я выбрал: Фильм1, Фильм2, Фильм3, Фильм4"
- Проанализируй выбранные фильмы, чтобы глубже понять вкусы пользователя
- ВАЖНО: Порекомендуй НОВЫЙ фильм, которого НЕ было в списке из 16 предложенных! Те 16 фильмов использовались только для понимания вкусов.
- Верни ТОЛЬКО валидный JSON с рекомендацией фильма (без пояснений, текста до/после, БЕЗ обрамляющих кавычек)
- Структура JSON должна быть строго такой:
{
  "title": "Название фильма",
  "release": "Год выпуска",
  "rating": число_рейтинг,
  "producer": "Продюсер",
  "actors": [
    {"lastName": "Фамилия", "firstName": "Имя"}
  ],
  "description": "Детальное объяснение, почему именно этот фильм идеально подходит пользователю с учетом всех его предпочтений, настроения, компании, возраста, пола и выбранных им фильмов"
}

Последовательность работы:
1. Задай достаточно вопросов для глубокого понимания (возраст, пол, жанры, настроение, компания, любимые фильмы/актёры/режиссёры и т.д.)
2. Предложи 16 фильмов для выбора (JSON type: "movie_selection")
3. Дождись выбора 4 фильмов от пользователя
4. Сделай финальную рекомендацию с учетом ВСЕЙ собранной информации

Твой JSON должен быть идеально отформатирован с отступом 2 пробела.
"""


JSON_SCHEMA_INSTRUCTION = (
    "Ты гном матершинник, живущий под мостом и пьющий пиво каждый день. Наполняй описание фильма матами и оскорблениями. Отвечай ТОЛЬКО валидным JSON без каких-либо пояснений, текста до/после и БЕЗ обрамляющих кавычек. "
    "Верни только JSON-объект, отформатированный с отступом 2 пробела. Если вопрос не о фильмах — верни JSON с полем 'error' и описанием ошибки. "
    "Структура данных для фильмов (рекомендуемая):\n"
    "{\n"
    "  \"$schema\": \"https://json-schema.org/draft/2020-12/schema\",\n"
    "  \"type\": \"object\",\n"
    "  \"properties\": {\n"
    "    \"actors\": {\n"
    "      \"type\": \"array\",\n"
    "      \"items\": {\n"
    "        \"type\": \"object\",\n"
    "        \"properties\": {\n"
    "          \"lastName\": { \"type\": \"string\" },\n"
    "          \"firstName\": { \"type\": \"string\" }\n"
    "        }\n"
    "      }\n"
    "    },\n"
    "    \"release\": { \"type\": \"string\" },\n"
    "    \"rating\": { \"type\": \"number\" },\n"
    "    \"producer\": { \"type\": \"string\" },\n"
    "    \"description\": { \"type\": \"string\" },\n"
    "    \"title\": { \"type\": \"string\" },\n"
    "    \"error\": { \"type\": \"string\" }\n"
    "  }\n"
    "}\n"
)


# Промпты для разных способов рассуждения
DIRECT_PROMPT = "Ответь на вопрос напрямую, кратко и по делу."

STEP_BY_STEP_PROMPT = """Реши задачу пошагово:
1. Сначала проанализируй условие задачи
2. Определи, какие шаги нужны для решения
3. Выполни каждый шаг последовательно
4. Сформулируй финальный ответ

Показывай своё рассуждение на каждом этапе."""

PROMPT_GENERATOR_INSTRUCTION = """Ты - эксперт по созданию промптов для AI моделей.
Твоя задача - создать оптимальный промпт для решения задачи, которую тебе предоставит пользователь.
Проанализируй задачу и создай детальный промпт, который поможет другой AI модели максимально эффективно решить эту задачу.
Верни только сам промпт, без дополнительных пояснений."""

EXPERT_PANEL_PROMPT = """Ты - модератор группы экспертов. В твоей команде есть 4 уникальных персонажа:

1. **Физик-ядерщик** - научный специалист с глубоким пониманием фундаментальных законов природы и строгой логикой. Анализирует задачу через призму научного метода, ищет объективные закономерности и причинно-следственные связи.

2. **Бабушка у подъезда** - житейски мудрая, имеет огромный практический опыт. Смотрит на задачу с точки зрения здравого смысла, народной мудрости и простых, понятных решений. Может рассказать поучительную историю из жизни.

3. **Ребёнок 7 лет** - чистый, незамутнённый взгляд на вещи. Задаёт простые, но глубокие вопросы. Не скован стереотипами, видит очевидное, которое взрослые часто упускают. Рассуждает просто и честно.

4. **300-летний робот из 2694 года** - искусственный интеллект с огромной базой знаний о будущем человечества. Анализирует задачу с позиции долгосрочной перспективы, технологического прогресса и футуристического мышления. Знает, как развивались события в следующие века.

Для решения задачи:
1. Дай слово Физику-ядерщику - пусть проанализирует задачу научно и структурированно
2. Дай слово Бабушке у подъезда - пусть даст житейский совет и поделится мудростью
3. Дай слово Ребёнку 7 лет - пусть посмотрит свежим взглядом и задаст простые вопросы
4. Дай слово Роботу из будущего - пусть предложит взгляд из 2694 года

Представь мнение каждого эксперта отдельно, с их уникальным стилем речи и мышления, а затем дай общий вывод, синтезирующий все точки зрения."""


def get_recommendation_agent_response(user_message):
    """Получает ответ от агента-рекомендатора фильмов"""
    use_agents_api = bool(config.get('agent_id'))
    url = (
        "https://llm.api.cloud.yandex.net/agents/v1/completions"
        if use_agents_api
        else "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    )
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {config['api_key']}"
    }

    # Формируем историю сообщений
    messages = [
        {
            "role": "system",
            "text": RECOMMENDATION_AGENT_PROMPT
        }
    ]

    # Добавляем историю диалога
    for msg in recommendation_history[-10:]:
        messages.append(msg)

    # Добавляем новое сообщение пользователя
    messages.append({"role": "user", "text": user_message})

    if use_agents_api:
        prompt = {
            "agentId": config["agent_id"],
            "messages": messages,
            "completionOptions": {
                "stream": False
            }
        }
    else:
        prompt = {
            "modelUri": f"gpt://{config['catalog_id']}/yandexgpt/latest",
            "completionOptions": {
                "stream": False,
                "temperature": 0.7,
                "maxTokens": 2000
            },
            "messages": messages
        }

    try:
        response = requests.post(url, headers=headers, json=prompt)
        response.raise_for_status()
        result = response.json()

        if "result" in result and "alternatives" in result["result"]:
            assistant_text = result["result"]["alternatives"][0]["message"]["text"]
            raw = assistant_text.strip()

            # Проверяем, является ли ответ JSON (финальная рекомендация)
            # Убираем markdown-блоки если есть
            if raw.startswith("```json"):
                raw = re.sub(r'^```json\s*', '', raw)
                raw = re.sub(r'\s*```$', '', raw)
            elif raw.startswith("```"):
                raw = re.sub(r'^```\s*', '', raw)
                raw = re.sub(r'\s*```$', '', raw)

            # Пытаемся распарсить как JSON
            parsed = None
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                # Если не JSON - возвращаем как есть (это вопрос агента)
                return assistant_text.strip()

            # Если это вторая попытка парсинга строки
            if isinstance(parsed, str):
                try:
                    parsed = json.loads(parsed)
                except json.JSONDecodeError:
                    return assistant_text.strip()

            # Если это JSON - форматируем красиво
            if parsed is not None and isinstance(parsed, dict):
                return json.dumps(parsed, ensure_ascii=False, indent=2)

            return assistant_text.strip()
        else:
            return "Извините, произошла ошибка при получении ответа."

    except requests.exceptions.RequestException as e:
        return f"Ошибка подключения к API: {str(e)}"
    except Exception as e:
        return f"Произошла ошибка: {str(e)}"


def get_agent_response(user_message):
    """Получает ответ от Yandex GPT агента в строгом JSON-формате"""
    # Если указан agent_id — используем Agents API (строгая схема применяется на стороне Агента)
    use_agents_api = bool(config.get('agent_id'))
    url = (
        "https://llm.api.cloud.yandex.net/agents/v1/completions"
        if use_agents_api
        else "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    )
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {config['api_key']}"
    }

    def empty_movie_object():
        return {
            "actors": [],
            "release": "",
            "rating": 0,
            "producer": "",
            "description": "",
            "title": ""
        }
    
    # Формируем историю сообщений
    messages = []
    if not use_agents_api:
        # Для raw completion оставляем системную инструкцию и few-shot
        messages = [
            {
                "role": "system",
                "text": JSON_SCHEMA_INSTRUCTION
            },
            {
                "role": "user",
                "text": "Пример запроса: Расскажи о фильме Матрица"
            },
            {
                "role": "assistant",
                "text": (
                    "{\n"
                    "  \"actors\": [\n"
                    "    { \"lastName\": \"Ривз\", \"firstName\": \"Киану\" }\n"
                    "  ],\n"
                    "  \"release\": \"1999\",\n"
                    "  \"rating\": 8.7,\n"
                    "  \"producer\": \"Джоэл Сильвер\",\n"
                    "  \"description\": \"Пример форматированного JSON без лишнего текста.\",\n"
                    "  \"title\": \"Матрица\"\n"
                    "}"
                )
            }
        ]
    
    # Добавляем историю диалога
    for msg in chat_history[-10:]:
        messages.append(msg)

    # Добавляем новое сообщение пользователя
    messages.append({"role": "user", "text": user_message})
    
    if use_agents_api:
        # Вызов через агент: строгая схема и все настройки из консоли агента
        prompt = {
            "agentId": config["agent_id"],
            "messages": messages,
            "completionOptions": {
                "stream": False
            }
        }
    else:
        # Прямой вызов модели
        prompt = {
            "modelUri": f"gpt://{config['catalog_id']}/yandexgpt-lite/latest",
            "completionOptions": {
                "stream": False,
                "temperature": 0.0,
                "maxTokens": 2000
            },
            "messages": messages
        }
    
    try:
        response = requests.post(url, headers=headers, json=prompt)
        response.raise_for_status()
        result = response.json()

        # Извлекаем текст ответа
        if "result" in result and "alternatives" in result["result"]:
            assistant_text = result["result"]["alternatives"][0]["message"]["text"]

            # Пытаемся гарантировать строгий JSON: парсим, расковыриваем кавычки, форматируем
            raw = assistant_text.strip()
            parsed = None
            # 1) прямая попытка распарсить
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = None

            # 2) если это строка с внутри-JSON ("{...}") — распарсим второй раз
            if isinstance(parsed, str):
                try:
                    parsed = json.loads(parsed)
                except json.JSONDecodeError:
                    parsed = None

            # 3) если всё ещё None — попробуем вырезать самый похожий на JSON блок
            if parsed is None:
                match = re.search(r"\{[\s\S]*\}", raw)
                if match:
                    candidate = match.group(0)
                    try:
                        parsed = json.loads(candidate)
                    except json.JSONDecodeError:
                        parsed = None

            if parsed is None:
                # жёсткий фолбэк: пустые поля
                return json.dumps(empty_movie_object(), ensure_ascii=False, indent=2)

            # Успешно: вернём красиво отформатированный JSON строкой (для фронта)
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        else:
            return json.dumps(empty_movie_object(), ensure_ascii=False, indent=2)
            
    except requests.exceptions.RequestException:
        return json.dumps(empty_movie_object(), ensure_ascii=False, indent=2)
    except Exception:
        return json.dumps(empty_movie_object(), ensure_ascii=False, indent=2)


def call_yandex_gpt(messages, temperature=0.7):
    """Универсальная функция для вызова Yandex GPT"""
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {config['api_key']}"
    }

    prompt = {
        "modelUri": f"gpt://{config['catalog_id']}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": temperature,
            "maxTokens": 2000
        },
        "messages": messages
    }

    try:
        response = requests.post(url, headers=headers, json=prompt)
        response.raise_for_status()
        result = response.json()

        if "result" in result and "alternatives" in result["result"]:
            return result["result"]["alternatives"][0]["message"]["text"]
        else:
            return "Ошибка: не удалось получить ответ"
    except Exception as e:
        return f"Ошибка: {str(e)}"


def solve_direct(task):
    """Способ 1: Прямой ответ без дополнительных инструкций"""
    messages = [
        {"role": "system", "text": DIRECT_PROMPT},
        {"role": "user", "text": task}
    ]
    return call_yandex_gpt(messages)


def solve_step_by_step(task):
    """Способ 2: Пошаговое решение"""
    messages = [
        {"role": "system", "text": STEP_BY_STEP_PROMPT},
        {"role": "user", "text": task}
    ]
    return call_yandex_gpt(messages)


def solve_with_prompt_generator(task):
    """Способ 3: Сначала генерируем промпт, затем решаем с его помощью"""
    # Шаг 1: Генерируем оптимальный промпт
    messages_generator = [
        {"role": "system", "text": PROMPT_GENERATOR_INSTRUCTION},
        {"role": "user", "text": f"Создай оптимальный промпт для решения следующей задачи:\n\n{task}"}
    ]
    generated_prompt = call_yandex_gpt(messages_generator)

    # Шаг 2: Используем сгенерированный промпт для решения задачи
    messages_solver = [
        {"role": "system", "text": generated_prompt},
        {"role": "user", "text": task}
    ]
    solution = call_yandex_gpt(messages_solver)

    # Возвращаем и промпт, и решение
    return f"=== СГЕНЕРИРОВАННЫЙ ПРОМПТ ===\n{generated_prompt}\n\n=== РЕШЕНИЕ С ИСПОЛЬЗОВАНИЕМ ПРОМПТА ===\n{solution}"


def solve_with_expert_panel(task):
    """Способ 4: Группа экспертов"""
    messages = [
        {"role": "system", "text": EXPERT_PANEL_PROMPT},
        {"role": "user", "text": task}
    ]
    return call_yandex_gpt(messages, temperature=0.8)


@app.route('/')
def index():
    """Главная страница с чатом"""
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    """Обработка сообщений чата"""
    data = request.json
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({'error': 'Пустое сообщение'}), 400

    # Сохраняем сообщение пользователя в историю
    chat_history.append({
        "role": "user",
        "text": user_message
    })

    # ДЕНЬ 9: Сохраняем в внешнюю память
    user_tokens = estimate_tokens(user_message)
    memory.save_message(current_session_id, "user", user_message, user_tokens)

    # Получаем ответ от агента
    assistant_response = get_agent_response(user_message)

    # Сохраняем ответ агента в историю
    chat_history.append({
        "role": "assistant",
        "text": assistant_response
    })

    # ДЕНЬ 9: Сохраняем ответ в внешнюю память
    assistant_tokens = estimate_tokens(assistant_response)
    memory.save_message(current_session_id, "assistant", assistant_response, assistant_tokens)

    return jsonify({
        'response': assistant_response
    })


@app.route('/recommend', methods=['POST'])
def recommend():
    """Обработка запросов к агенту-рекомендатору"""
    data = request.json
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({'error': 'Пустое сообщение'}), 400

    # Сохраняем сообщение пользователя в историю рекомендаций
    recommendation_history.append({
        "role": "user",
        "text": user_message
    })

    # Получаем ответ от агента-рекомендатора
    assistant_response = get_recommendation_agent_response(user_message)

    # Сохраняем ответ агента в историю
    recommendation_history.append({
        "role": "assistant",
        "text": assistant_response
    })

    # Проверяем, является ли ответ JSON (финальная рекомендация)
    try:
        # Пытаемся распарсить как JSON
        json.loads(assistant_response)
        is_final_recommendation = True
    except json.JSONDecodeError:
        is_final_recommendation = False

    return jsonify({
        'response': assistant_response,
        'is_final': is_final_recommendation
    })


@app.route('/clear', methods=['POST'])
def clear_history():
    """Очистка истории чата"""
    global chat_history
    chat_history = []
    return jsonify({'status': 'ok'})


@app.route('/clear_recommendations', methods=['POST'])
def clear_recommendations():
    """Очистка истории рекомендаций"""
    global recommendation_history
    recommendation_history = []
    return jsonify({'status': 'ok'})


@app.route('/reasoning', methods=['POST'])
def reasoning():
    """Решение задачи разными способами рассуждения"""
    data = request.json
    task = data.get('task', '').strip()
    method = data.get('method', 'all')  # all, direct, step_by_step, prompt_generator, expert_panel

    if not task:
        return jsonify({'error': 'Задача не указана'}), 400

    results = {}

    try:
        if method == 'all' or method == 'direct':
            results['direct'] = solve_direct(task)

        if method == 'all' or method == 'step_by_step':
            results['step_by_step'] = solve_step_by_step(task)

        if method == 'all' or method == 'prompt_generator':
            results['prompt_generator'] = solve_with_prompt_generator(task)

        if method == 'all' or method == 'expert_panel':
            results['expert_panel'] = solve_with_expert_panel(task)

        return jsonify({
            'task': task,
            'method': method,
            'results': results
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/temperature_experiment', methods=['POST'])
def temperature_experiment():
    """Эксперимент с разными значениями температуры"""
    data = request.json
    prompt = data.get('prompt', '').strip()

    if not prompt:
        return jsonify({'error': 'Запрос не указан'}), 400

    # Значения температуры для сравнения (0.0 - 1.0)
    temperatures = [0.0, 0.5, 1.0]
    results = {}

    try:
        # Запускаем один и тот же запрос с разными температурами
        for temp in temperatures:
            messages = [
                {"role": "user", "text": prompt}
            ]
            response = call_yandex_gpt(messages, temperature=temp)
            results[str(temp)] = response

        # Добавляем анализ результатов
        analysis = {
            'prompt': prompt,
            'temperatures': {
                '0.0': {
                    'response': results['0.0'],
                    'description': 'Детерминированный режим - максимальная точность и предсказуемость'
                },
                '0.5': {
                    'response': results['0.5'],
                    'description': 'Сбалансированный режим - умеренная креативность с сохранением точности'
                },
                '1.0': {
                    'response': results['1.0'],
                    'description': 'Креативный режим - максимальная вариативность и оригинальность'
                }
            },
            'recommendations': {
                '0.0': 'Подходит для: фактических запросов, технической документации, точных вычислений, переводов',
                '0.5': 'Подходит для: общения, рассказов, объяснений, советов, деловой переписки',
                '1.0': 'Подходит для: креативного письма, генерации идей, художественных текстов, нестандартных решений'
            }
        }

        return jsonify(analysis)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Функция для подсчета токенов (приблизительная оценка)
def estimate_tokens(text: str) -> int:
    """Приблизительная оценка количества токенов"""
    # Простая эвристика: ~4 символа = 1 токен для английского
    # Для русского языка: ~6 символов = 1 токен
    words = text.split()
    chars = len(text)
    # Среднее между словами и символами
    return max(len(words), chars // 5)


# Доступные модели Yandex Cloud
YANDEX_MODELS = {
    'yandexgpt-lite': {
        'uri': 'yandexgpt-lite/latest',
        'name': 'YandexGPT Lite',
        'description': 'Легковесная модель для быстрых ответов',
        'pricing': {'input': 0.2, 'output': 0.6}  # руб за 1K токенов
    },
    'yandexgpt': {
        'uri': 'yandexgpt/latest',
        'name': 'YandexGPT',
        'description': 'Стандартная модель с балансом качества и скорости',
        'pricing': {'input': 0.4, 'output': 1.2}
    },
    'yandexgpt-32k': {
        'uri': 'yandexgpt-32k/rc',
        'name': 'YandexGPT 32K',
        'description': 'Модель с расширенным контекстом',
        'pricing': {'input': 0.8, 'output': 2.4}
    },
    'summarization': {
        'uri': 'summarization/latest',
        'name': 'Summarization',
        'description': 'Специализированная модель для суммаризации',
        'pricing': {'input': 0.4, 'output': 1.2}
    }
}


def call_yandex_model(model_key: str, prompt: str) -> Dict[str, Any]:
    """
    Вызов модели Yandex Cloud через Foundation Models API
    Возвращает результат с метриками
    """
    if model_key not in YANDEX_MODELS:
        return {
            'success': False,
            'model': model_key,
            'error': f"Неизвестная модель: {model_key}",
            'metrics': {'response_time': 0}
        }

    model_info = YANDEX_MODELS[model_key]
    model_uri = model_info['uri']

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {config['api_key']}"
    }

    payload = {
        "modelUri": f"gpt://{config['catalog_id']}/{model_uri}",
        "completionOptions": {
            "stream": False,
            "temperature": 0.7,
            "maxTokens": 8000  # Максимальный лимит - модель не ограничена
        },
        "messages": [
            {"role": "user", "text": prompt}
        ]
    }

    start_time = time.time()

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=180)  # Увеличен до 3 минут для больших запросов
        elapsed_time = time.time() - start_time

        if response.status_code == 200:
            result = response.json()

            # Извлечение текста ответа
            generated_text = ""
            input_tokens = 0
            output_tokens = 0

            if "result" in result and "alternatives" in result["result"]:
                generated_text = result["result"]["alternatives"][0]["message"]["text"]

                # Получаем реальные метрики токенов из ответа
                usage = result["result"].get("usage", {})
                # Явно преобразуем в int, API может вернуть строки
                input_tokens = int(usage.get("inputTextTokens", estimate_tokens(prompt)))
                output_tokens = int(usage.get("completionTokens", estimate_tokens(generated_text)))

            total_tokens = input_tokens + output_tokens

            # Расчет стоимости в рублях
            pricing = model_info['pricing']
            cost_rub = (float(input_tokens) * pricing['input'] + float(output_tokens) * pricing['output']) / 1000

            return {
                'success': True,
                'model': model_key,
                'model_name': model_info['name'],
                'response': generated_text,
                'metrics': {
                    'response_time': float(round(elapsed_time, 3)),
                    'input_tokens': int(input_tokens),
                    'output_tokens': int(output_tokens),
                    'total_tokens': int(total_tokens),
                    'cost_rub': float(round(cost_rub, 4)),
                    'is_free': False
                }
            }
        else:
            return {
                'success': False,
                'model': model_key,
                'model_name': model_info['name'],
                'error': f"HTTP {response.status_code}: {response.text[:200]}",
                'metrics': {
                    'response_time': float(round(time.time() - start_time, 3))
                }
            }

    except Exception as e:
        return {
            'success': False,
            'model': model_key,
            'model_name': model_info.get('name', model_key),
            'error': str(e),
            'metrics': {
                'response_time': float(round(time.time() - start_time, 3))
            }
        }


@app.route('/token_test', methods=['POST'])
def token_test():
    """Тестирование токенов с разными размерами запросов"""
    data = request.json
    prompt = data.get('prompt', '').strip()
    test_type = data.get('test_type', 'short')  # short, long, extreme

    if not prompt:
        return jsonify({'error': 'Запрос не указан'}), 400

    # Оценка количества токенов в запросе
    estimated_input_tokens = estimate_tokens(prompt)

    try:
        # Для экстремального теста пробуем обе модели для наглядного сравнения
        if test_type == 'extreme':
            # Сначала пробуем базовую модель (лимит 8000 токенов)
            result_base = call_yandex_model('yandexgpt', prompt)
            # Затем пробуем 32K модель (лимит 32000 токенов)
            result_32k = call_yandex_model('yandexgpt-32k', prompt)

            response_data = {
                'test_type': test_type,
                'prompt': prompt,
                'prompt_length': len(prompt),
                'estimated_input_tokens': estimated_input_tokens,
                'comparison_mode': True,
                'base_model': {
                    'model_key': 'yandexgpt',
                    'model_name': YANDEX_MODELS['yandexgpt']['name'],
                    'model_limit': 8000,
                    'result': result_base
                },
                'extended_model': {
                    'model_key': 'yandexgpt-32k',
                    'model_name': YANDEX_MODELS['yandexgpt-32k']['name'],
                    'model_limit': 32000,
                    'result': result_32k
                }
            }

            # Анализ для базовой модели
            if result_base['success']:
                actual_input = result_base['metrics']['input_tokens']
                response_data['base_model']['analysis'] = {
                    'within_limit': actual_input < 8000,
                    'limit_usage_percent': round((actual_input / 8000) * 100, 1)
                }
            else:
                response_data['base_model']['analysis'] = {
                    'within_limit': False,
                    'error': 'Превышен лимит или ошибка API'
                }

            # Анализ для 32K модели
            if result_32k['success']:
                actual_input = result_32k['metrics']['input_tokens']
                response_data['extended_model']['analysis'] = {
                    'within_limit': actual_input < 32000,
                    'limit_usage_percent': round((actual_input / 32000) * 100, 1)
                }
            else:
                response_data['extended_model']['analysis'] = {
                    'within_limit': False,
                    'error': 'Превышен лимит или ошибка API'
                }

            return jsonify(response_data)

        else:
            # Для коротких и длинных запросов используем стандартную модель
            model_key = 'yandexgpt'
            result = call_yandex_model(model_key, prompt)

            # Добавляем дополнительную информацию
            response_data = {
                'test_type': test_type,
                'prompt': prompt,
                'prompt_length': len(prompt),
                'estimated_input_tokens': estimated_input_tokens,
                'model_used': model_key,
                'model_name': YANDEX_MODELS[model_key]['name'],
                'model_limit': 8000,
                'comparison_mode': False,
                'result': result
            }

            # Анализ результата
            if result['success']:
                actual_input_tokens = result['metrics']['input_tokens']
                actual_output_tokens = result['metrics']['output_tokens']
                total_tokens = result['metrics']['total_tokens']

                response_data['analysis'] = {
                    'within_limit': actual_input_tokens < response_data['model_limit'],
                    'token_efficiency': round((actual_output_tokens / actual_input_tokens) if actual_input_tokens > 0 else 0, 2),
                    'cost_per_token': round(result['metrics']['cost_rub'] / total_tokens, 6) if total_tokens > 0 else 0,
                    'response_quality': 'Ответ получен успешно' if actual_output_tokens > 50 else 'Короткий ответ'
                }
            else:
                response_data['analysis'] = {
                    'within_limit': False,
                    'error_type': 'API Error' if 'HTTP' in result['error'] else 'Unknown Error'
                }

            return jsonify(response_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/model_comparison', methods=['POST'])
def model_comparison():
    """Сравнение разных моделей Yandex AI с замером метрик"""
    data = request.json
    prompt = data.get('prompt', '').strip()
    models = data.get('models', [])

    if not prompt:
        return jsonify({'error': 'Запрос не указан'}), 400

    if not models or len(models) < 2:
        return jsonify({'error': 'Необходимо выбрать минимум 2 модели для сравнения'}), 400

    results = []

    try:
        # Вызываем каждую модель
        for model_key in models:
            result = call_yandex_model(model_key, prompt)
            results.append(result)

        # Добавляем сравнительный анализ
        successful_results = [r for r in results if r['success']]

        comparison = {
            'prompt': prompt,
            'models_compared': len(models),
            'successful_calls': len(successful_results),
            'results': results
        }

        if successful_results:
            # Находим самую быструю и медленную модель
            fastest = min(successful_results, key=lambda x: x['metrics']['response_time'])
            slowest = max(successful_results, key=lambda x: x['metrics']['response_time'])

            # Находим модель с наименьшим количеством токенов
            most_concise = min(successful_results, key=lambda x: x['metrics']['output_tokens'])
            most_verbose = max(successful_results, key=lambda x: x['metrics']['output_tokens'])

            # Находим самую дешевую и дорогую
            cheapest = min(successful_results, key=lambda x: x['metrics']['cost_rub'])
            most_expensive = max(successful_results, key=lambda x: x['metrics']['cost_rub'])

            comparison['analysis'] = {
                'fastest_model': fastest.get('model_name', fastest['model']),
                'fastest_time': fastest['metrics']['response_time'],
                'slowest_model': slowest.get('model_name', slowest['model']),
                'slowest_time': slowest['metrics']['response_time'],
                'most_concise_model': most_concise.get('model_name', most_concise['model']),
                'most_concise_tokens': most_concise['metrics']['output_tokens'],
                'most_verbose_model': most_verbose.get('model_name', most_verbose['model']),
                'most_verbose_tokens': most_verbose['metrics']['output_tokens'],
                'cheapest_model': cheapest.get('model_name', cheapest['model']),
                'cheapest_cost': cheapest['metrics']['cost_rub'],
                'most_expensive_model': most_expensive.get('model_name', most_expensive['model']),
                'most_expensive_cost': most_expensive['metrics']['cost_rub'],
                'avg_response_time': round(sum(r['metrics']['response_time'] for r in successful_results) / len(successful_results), 3),
                'avg_output_tokens': round(sum(r['metrics']['output_tokens'] for r in successful_results) / len(successful_results), 1),
                'avg_cost': round(sum(r['metrics']['cost_rub'] for r in successful_results) / len(successful_results), 4)
            }

        return jsonify(comparison)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/compression_test', methods=['POST'])
def compression_test():
    """
    Тестирование механизма компрессии диалога (День 8).
    Сравнивает работу агента с полной историей и со сжатой.
    """
    data = request.json
    message = data.get('message', '').strip()
    action = data.get('action', 'send')  # send, stats, clear, compare

    if action == 'clear':
        # Очистка истории
        dialog_manager.clear()
        return jsonify({
            'status': 'ok',
            'message': 'История диалога очищена'
        })

    elif action == 'stats':
        # Получение статистики
        stats = dialog_manager.get_stats()
        return jsonify({
            'status': 'ok',
            'stats': stats
        })

    elif action == 'compare':
        # Сравнение работы с компрессией и без
        if not message:
            return jsonify({'error': 'Сообщение не указано'}), 400

        try:
            # Создаем два независимых менеджера для честного сравнения
            manager_with_compression = DialogHistoryManager(compression_threshold=10, use_compression=True)
            manager_without_compression = DialogHistoryManager(compression_threshold=10, use_compression=False)

            # Копируем текущую историю в оба менеджера
            for msg in dialog_manager.messages:
                manager_with_compression.add_message(msg['role'], msg['text'])
                manager_without_compression.add_message(msg['role'], msg['text'])

            # Добавляем новое сообщение
            manager_with_compression.add_message('user', message)
            manager_without_compression.add_message('user', message)

            # Получаем ответы с обоих вариантов истории
            # С компрессией
            start_time = time.time()
            history_compressed = manager_with_compression.get_history_for_api(use_compressed=True)
            messages_compressed = [{"role": "user", "text": message}]
            if len(history_compressed) > 0:
                messages_compressed = history_compressed + [{"role": "user", "text": message}]

            response_compressed = call_yandex_gpt(messages_compressed, temperature=0.7)
            time_compressed = time.time() - start_time

            # Без компрессии
            start_time = time.time()
            history_full = manager_without_compression.get_history_for_api(use_compressed=False)
            messages_full = [{"role": "user", "text": message}]
            if len(history_full) > 0:
                messages_full = history_full + [{"role": "user", "text": message}]

            response_full = call_yandex_gpt(messages_full, temperature=0.7)
            time_full = time.time() - start_time

            # Подсчет токенов
            tokens_compressed_input = sum(estimate_tokens(msg['text']) for msg in messages_compressed)
            tokens_compressed_output = estimate_tokens(response_compressed)

            tokens_full_input = sum(estimate_tokens(msg['text']) for msg in messages_full)
            tokens_full_output = estimate_tokens(response_full)

            # Расчет стоимости (используем цены YandexGPT)
            pricing = YANDEX_MODELS['yandexgpt']['pricing']
            cost_compressed = (tokens_compressed_input * pricing['input'] + tokens_compressed_output * pricing['output']) / 1000
            cost_full = (tokens_full_input * pricing['input'] + tokens_full_output * pricing['output']) / 1000

            # Добавляем ответ агента в главный менеджер
            dialog_manager.add_message('user', message)
            dialog_manager.add_message('assistant', response_compressed)

            comparison_result = {
                'with_compression': {
                    'response': response_compressed,
                    'metrics': {
                        'response_time': round(time_compressed, 3),
                        'input_tokens': tokens_compressed_input,
                        'output_tokens': tokens_compressed_output,
                        'total_tokens': tokens_compressed_input + tokens_compressed_output,
                        'cost_rub': round(cost_compressed, 4),
                        'history_messages': len(messages_compressed) - 1  # Минус текущее сообщение
                    }
                },
                'without_compression': {
                    'response': response_full,
                    'metrics': {
                        'response_time': round(time_full, 3),
                        'input_tokens': tokens_full_input,
                        'output_tokens': tokens_full_output,
                        'total_tokens': tokens_full_input + tokens_full_output,
                        'cost_rub': round(cost_full, 4),
                        'history_messages': len(messages_full) - 1  # Минус текущее сообщение
                    }
                },
                'savings': {
                    'tokens_saved': tokens_full_input - tokens_compressed_input,
                    'tokens_saved_percent': round((1 - tokens_compressed_input / tokens_full_input) * 100, 2) if tokens_full_input > 0 else 0,
                    'cost_saved': round(cost_full - cost_compressed, 4),
                    'cost_saved_percent': round((1 - cost_compressed / cost_full) * 100, 2) if cost_full > 0 else 0,
                    'time_difference': round(time_full - time_compressed, 3)
                },
                'compression_stats': manager_with_compression.get_stats()
            }

            return jsonify({
                'status': 'ok',
                'comparison': comparison_result
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    elif action == 'run_test':
        # Автоматический тест компрессии
        try:
            # Очищаем историю перед тестом
            dialog_manager.clear()

            # Серия тестовых сообщений (упрощенная версия)
            test_messages = [
                "Расскажи о Python",
                "Что такое Django?",
                "Как работает Flask?",
                "Что такое FastAPI?",
                "Сравни Django и Flask",
                "Какие есть ORM для Python?",
                "Что такое SQLAlchemy?",
                "Как работает async/await?",
                "Что такое asyncio?",
                "Объясни декораторы в Python",
                "Что такое генераторы?",
                "Как работает yield?",
            ]

            total_tokens = 0
            total_cost = 0
            start_time_total = time.time()

            # Отправляем сообщения
            for message in test_messages:
                # Добавляем сообщение пользователя
                dialog_manager.add_message('user', message)

                # Получаем историю для API
                history = dialog_manager.get_history_for_api()
                messages = history.copy()

                # Получаем ответ от модели
                response = call_yandex_gpt(messages, temperature=0.7)

                # Добавляем ответ в историю
                dialog_manager.add_message('assistant', response)

                # Подсчет токенов
                input_tokens = sum(estimate_tokens(msg['text']) for msg in messages)
                output_tokens = estimate_tokens(response)
                total_tokens += input_tokens + output_tokens

                # Расчет стоимости
                pricing = YANDEX_MODELS['yandexgpt']['pricing']
                cost = (input_tokens * pricing['input'] + output_tokens * pricing['output']) / 1000
                total_cost += cost

            total_time = time.time() - start_time_total

            # Получаем финальную статистику
            final_stats = dialog_manager.get_stats()

            # Делаем финальное сравнение
            test_question = "Какой фреймворк лучше выбрать для веб-разработки?"

            # Создаем два независимых менеджера для честного сравнения
            manager_with = DialogHistoryManager(compression_threshold=10, use_compression=True)
            manager_without = DialogHistoryManager(compression_threshold=10, use_compression=False)

            # Копируем текущую историю
            for msg in dialog_manager.messages:
                manager_with.add_message(msg['role'], msg['text'])
                manager_without.add_message(msg['role'], msg['text'])

            # Добавляем тестовый вопрос
            manager_with.add_message('user', test_question)
            manager_without.add_message('user', test_question)

            # С компрессией
            start_time = time.time()
            history_compressed = manager_with.get_history_for_api(use_compressed=True)
            messages_compressed = history_compressed + [{"role": "user", "text": test_question}] if history_compressed else [{"role": "user", "text": test_question}]
            response_compressed = call_yandex_gpt(messages_compressed, temperature=0.7)
            time_compressed = time.time() - start_time

            # Без компрессии
            start_time = time.time()
            history_full = manager_without.get_history_for_api(use_compressed=False)
            messages_full = history_full + [{"role": "user", "text": test_question}] if history_full else [{"role": "user", "text": test_question}]
            response_full = call_yandex_gpt(messages_full, temperature=0.7)
            time_full = time.time() - start_time

            # Подсчет токенов для сравнения
            tokens_compressed_input = sum(estimate_tokens(msg['text']) for msg in messages_compressed)
            tokens_compressed_output = estimate_tokens(response_compressed)
            tokens_full_input = sum(estimate_tokens(msg['text']) for msg in messages_full)
            tokens_full_output = estimate_tokens(response_full)

            # Расчет стоимости
            pricing = YANDEX_MODELS['yandexgpt']['pricing']
            cost_compressed = (tokens_compressed_input * pricing['input'] + tokens_compressed_output * pricing['output']) / 1000
            cost_full = (tokens_full_input * pricing['input'] + tokens_full_output * pricing['output']) / 1000

            comparison_result = {
                'with_compression': {
                    'response': response_compressed,
                    'metrics': {
                        'response_time': round(time_compressed, 3),
                        'input_tokens': tokens_compressed_input,
                        'output_tokens': tokens_compressed_output,
                        'total_tokens': tokens_compressed_input + tokens_compressed_output,
                        'cost_rub': round(cost_compressed, 4),
                        'history_messages': len(messages_compressed) - 1
                    }
                },
                'without_compression': {
                    'response': response_full,
                    'metrics': {
                        'response_time': round(time_full, 3),
                        'input_tokens': tokens_full_input,
                        'output_tokens': tokens_full_output,
                        'total_tokens': tokens_full_input + tokens_full_output,
                        'cost_rub': round(cost_full, 4),
                        'history_messages': len(messages_full) - 1
                    }
                },
                'savings': {
                    'tokens_saved': tokens_full_input - tokens_compressed_input,
                    'tokens_saved_percent': round((1 - tokens_compressed_input / tokens_full_input) * 100, 2) if tokens_full_input > 0 else 0,
                    'cost_saved': round(cost_full - cost_compressed, 4),
                    'cost_saved_percent': round((1 - cost_compressed / cost_full) * 100, 2) if cost_full > 0 else 0,
                    'time_difference': round(time_full - time_compressed, 3)
                }
            }

            return jsonify({
                'status': 'ok',
                'messages_sent': len(test_messages),
                'total_time': round(total_time, 2),
                'total_tokens': total_tokens,
                'total_cost': round(total_cost, 4),
                'final_stats': final_stats,
                'comparison': comparison_result
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    elif action == 'send':
        # Обычная отправка сообщения с компрессией
        if not message:
            return jsonify({'error': 'Сообщение не указано'}), 400

        try:
            # Добавляем сообщение пользователя и проверяем, произошла ли компрессия
            compression_triggered = dialog_manager.add_message('user', message)

            # Получаем историю для API
            history = dialog_manager.get_history_for_api()

            # Формируем сообщения для API
            messages = history.copy()

            # Получаем ответ от модели
            start_time = time.time()
            response = call_yandex_gpt(messages, temperature=0.7)
            response_time = time.time() - start_time

            # Добавляем ответ в историю
            dialog_manager.add_message('assistant', response)

            # Подсчет токенов
            input_tokens = sum(estimate_tokens(msg['text']) for msg in messages)
            output_tokens = estimate_tokens(response)
            total_tokens = input_tokens + output_tokens

            # Расчет стоимости
            pricing = YANDEX_MODELS['yandexgpt']['pricing']
            cost = (input_tokens * pricing['input'] + output_tokens * pricing['output']) / 1000

            # Получаем статистику
            stats = dialog_manager.get_stats()

            return jsonify({
                'status': 'ok',
                'response': response,
                'compression_triggered': compression_triggered,
                'metrics': {
                    'response_time': round(response_time, 3),
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'total_tokens': total_tokens,
                    'cost_rub': round(cost, 4)
                },
                'compression_stats': stats
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    else:
        return jsonify({'error': f'Неизвестное действие: {action}'}), 400


# ==================== ВНЕШНЯЯ ПАМЯТЬ (ДЕНЬ 9) ====================

@app.route('/memory/sessions', methods=['GET', 'POST'])
def manage_sessions():
    """Управление сессиями диалогов"""
    global current_session_id

    if request.method == 'GET':
        # Получить список сессий
        sessions = memory.list_sessions(limit=50)
        return jsonify({
            'status': 'ok',
            'current_session': current_session_id,
            'sessions': sessions
        })

    elif request.method == 'POST':
        # Создать или переключиться на сессию
        data = request.json
        action = data.get('action', 'create')

        if action == 'create':
            # Создать новую сессию
            session_id = str(uuid.uuid4())
            title = data.get('title', f'Сессия {datetime.now().strftime("%Y-%m-%d %H:%M")}')
            metadata = data.get('metadata', {})

            if memory.create_session(session_id, title, metadata):
                current_session_id = session_id
                return jsonify({
                    'status': 'ok',
                    'session_id': session_id,
                    'message': 'Сессия создана'
                })
            else:
                return jsonify({'error': 'Не удалось создать сессию'}), 500

        elif action == 'switch':
            # Переключиться на существующую сессию
            session_id = data.get('session_id')
            if not session_id:
                return jsonify({'error': 'session_id не указан'}), 400

            session = memory.get_session(session_id)
            if session:
                current_session_id = session_id
                # Загружаем историю сообщений сессии
                messages = memory.get_messages(session_id)
                return jsonify({
                    'status': 'ok',
                    'session': session,
                    'messages': messages,
                    'message': 'Сессия загружена'
                })
            else:
                return jsonify({'error': 'Сессия не найдена'}), 404

        elif action == 'delete':
            # Удалить сессию
            session_id = data.get('session_id')
            if not session_id:
                return jsonify({'error': 'session_id не указан'}), 400

            if memory.delete_session(session_id):
                # Если удалили текущую сессию, создаем новую
                if session_id == current_session_id:
                    current_session_id = str(uuid.uuid4())
                    memory.create_session(current_session_id, 'Новая сессия')

                return jsonify({
                    'status': 'ok',
                    'message': 'Сессия удалена',
                    'current_session': current_session_id
                })
            else:
                return jsonify({'error': 'Не удалось удалить сессию'}), 500


@app.route('/memory/messages', methods=['GET'])
def get_session_messages():
    """Получить историю сообщений текущей сессии"""
    limit = request.args.get('limit', type=int, default=None)
    messages = memory.get_messages(current_session_id, limit)

    return jsonify({
        'status': 'ok',
        'session_id': current_session_id,
        'count': len(messages),
        'messages': messages
    })


@app.route('/memory/memories', methods=['GET', 'POST', 'DELETE'])
def manage_memories():
    """Управление долговременной памятью"""

    if request.method == 'GET':
        # Получить все записи памяти или по категории
        category = request.args.get('category')

        if category:
            memories_list = memory.get_memories_by_category(category)
        else:
            limit = request.args.get('limit', type=int, default=50)
            memories_list = memory.list_all_memories(limit)

        return jsonify({
            'status': 'ok',
            'count': len(memories_list),
            'memories': memories_list
        })

    elif request.method == 'POST':
        # Сохранить запись в память
        data = request.json
        key = data.get('key')
        value = data.get('value')
        category = data.get('category', 'general')
        importance = data.get('importance', 5)
        metadata = data.get('metadata')

        if not key or value is None:
            return jsonify({'error': 'key и value обязательны'}), 400

        if memory.save_memory(key, value, category, importance, metadata):
            return jsonify({
                'status': 'ok',
                'message': 'Запись сохранена в память'
            })
        else:
            return jsonify({'error': 'Не удалось сохранить'}), 500

    elif request.method == 'DELETE':
        # Удалить запись из памяти
        data = request.json
        key = data.get('key')

        if not key:
            return jsonify({'error': 'key обязателен'}), 400

        if memory.delete_memory(key):
            return jsonify({
                'status': 'ok',
                'message': 'Запись удалена'
            })
        else:
            return jsonify({'error': 'Запись не найдена'}), 404


@app.route('/memory/context', methods=['GET', 'POST', 'DELETE'])
def manage_context():
    """Управление промежуточным контекстом сессии"""

    if request.method == 'GET':
        # Получить весь контекст или конкретное значение
        key = request.args.get('key')

        if key:
            value = memory.get_context(current_session_id, key)
            if value is not None:
                return jsonify({
                    'status': 'ok',
                    'key': key,
                    'value': value
                })
            else:
                return jsonify({'error': 'Ключ не найден'}), 404
        else:
            context = memory.get_all_context(current_session_id)
            return jsonify({
                'status': 'ok',
                'session_id': current_session_id,
                'context': context
            })

    elif request.method == 'POST':
        # Сохранить значение в контекст
        data = request.json
        key = data.get('key')
        value = data.get('value')

        if not key or value is None:
            return jsonify({'error': 'key и value обязательны'}), 400

        if memory.save_context(current_session_id, key, value):
            return jsonify({
                'status': 'ok',
                'message': 'Контекст сохранен'
            })
        else:
            return jsonify({'error': 'Не удалось сохранить'}), 500

    elif request.method == 'DELETE':
        # Удалить контекст
        data = request.json
        key = data.get('key')  # Если None - удалится весь контекст

        if memory.delete_context(current_session_id, key):
            return jsonify({
                'status': 'ok',
                'message': 'Контекст удален'
            })
        else:
            return jsonify({'error': 'Не удалось удалить'}), 404


@app.route('/memory/stats', methods=['GET'])
def memory_stats():
    """Получить статистику использования памяти"""
    stats = memory.get_stats()

    # Добавляем информацию о текущей сессии
    session = memory.get_session(current_session_id)
    message_count = memory.get_message_count(current_session_id)

    return jsonify({
        'status': 'ok',
        'stats': stats,
        'current_session': {
            'session_id': current_session_id,
            'info': session,
            'message_count': message_count
        }
    })


@app.route('/memory/test', methods=['POST'])
def memory_test():
    """Тестирование системы памяти"""
    data = request.json
    action = data.get('action', 'full_test')

    try:
        if action == 'full_test':
            # Полный тест всех функций памяти
            test_results = []

            # 1. Создание тестовой сессии
            test_session_id = f"test_{uuid.uuid4()}"
            result = memory.create_session(test_session_id, "Тестовая сессия", {"test": True})
            test_results.append({
                'test': 'Создание сессии',
                'success': result
            })

            # 2. Сохранение сообщений
            message_saved = memory.save_message(test_session_id, "user", "Тестовое сообщение пользователя", 10)
            message_saved &= memory.save_message(test_session_id, "assistant", "Тестовый ответ ассистента", 20)
            test_results.append({
                'test': 'Сохранение сообщений',
                'success': message_saved
            })

            # 3. Загрузка сообщений
            messages = memory.get_messages(test_session_id)
            test_results.append({
                'test': 'Загрузка сообщений',
                'success': len(messages) == 2,
                'data': messages
            })

            # 4. Сохранение в долговременную память
            memory_saved = memory.save_memory(
                "test_fact",
                {"fact": "Python - отличный язык программирования"},
                "test",
                8
            )
            test_results.append({
                'test': 'Сохранение в долговременную память',
                'success': memory_saved
            })

            # 5. Чтение из долговременной памяти
            fact = memory.get_memory("test_fact")
            test_results.append({
                'test': 'Чтение из долговременной памяти',
                'success': fact is not None,
                'data': fact
            })

            # 6. Сохранение контекста
            context_saved = memory.save_context(test_session_id, "current_task", "Тестирование памяти")
            context_saved &= memory.save_context(test_session_id, "step", 1)
            test_results.append({
                'test': 'Сохранение контекста',
                'success': context_saved
            })

            # 7. Чтение контекста
            context = memory.get_all_context(test_session_id)
            test_results.append({
                'test': 'Чтение контекста',
                'success': len(context) == 2,
                'data': context
            })

            # 8. Очистка тестовых данных
            memory.delete_session(test_session_id)
            memory.delete_memory("test_fact")

            # Проверяем общую статистику
            stats = memory.get_stats()

            return jsonify({
                'status': 'ok',
                'test_results': test_results,
                'all_passed': all(r['success'] for r in test_results),
                'stats': stats
            })

        elif action == 'persistence_test':
            # Тест на сохранение данных между "запусками"
            # Сохраняем данные
            test_key = f"persistence_test_{int(time.time())}"
            test_value = {
                "timestamp": datetime.now().isoformat(),
                "data": "Это данные должны сохраниться"
            }

            memory.save_memory(test_key, test_value, "persistence_test", 10)

            # Пытаемся прочитать
            loaded_value = memory.get_memory(test_key)

            success = loaded_value is not None and loaded_value.get('data') == test_value['data']

            return jsonify({
                'status': 'ok',
                'test': 'Тест персистентности',
                'success': success,
                'saved': test_value,
                'loaded': loaded_value,
                'message': 'Данные сохранены в БД. Перезапустите приложение и проверьте через /memory/memories'
            })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


if __name__ == '__main__':
    # Создаем начальную сессию при запуске
    memory.create_session(current_session_id, f'Сессия {datetime.now().strftime("%Y-%m-%d %H:%M")}')

    app.run(debug=True, host='0.0.0.0', port=5005)

