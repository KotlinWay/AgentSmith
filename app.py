from flask import Flask, render_template, request, jsonify
import requests
import json
import os
import re

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

EXPERT_PANEL_PROMPT = """Ты - модератор группы экспертов. В твоей команде есть:
1. Логик - специалист по логическому анализу и структурированному мышлению
2. Креативщик - специалист по нестандартным решениям и творческому подходу
3. Критик - специалист по поиску ошибок и слабых мест в рассуждениях
4. Синтезатор - специалист по объединению разных точек зрения в единое решение

Для решения задачи:
1. Дай слово Логику - пусть проанализирует задачу структурированно
2. Дай слово Креативщику - пусть предложит нестандартные подходы
3. Дай слово Критику - пусть найдет слабые места в предложенных решениях
4. Дай слово Синтезатору - пусть объединит лучшее и даст финальный ответ

Представь мнение каждого эксперта отдельно, а затем общий вывод."""


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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5005)

