from flask import Flask, render_template, request, jsonify
import requests
import json
import os
import re
import time
from typing import Dict, Any

app = Flask(__name__)

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
    
    # Получаем ответ от агента
    assistant_response = get_agent_response(user_message)
    
    # Сохраняем ответ агента в историю
    chat_history.append({
        "role": "assistant",
        "text": assistant_response
    })
    
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
            "maxTokens": 2000  # Увеличено до 2000 для более полных ответов
        },
        "messages": [
            {"role": "user", "text": prompt}
        ]
    }

    start_time = time.time()

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5005)

