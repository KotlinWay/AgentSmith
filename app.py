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


RECOMMENDATION_AGENT_PROMPT = """
Ты умный агент-советник по фильмам. Твоя задача - помочь пользователю найти идеальный фильм через диалог.

ВАЖНО: Ты работаешь в двух режимах:

РЕЖИМ 1 - СБОР ИНФОРМАЦИИ (обычный текст):
- Веди естественный, дружелюбный диалог с пользователем
- Задавай вопросы о его предпочтениях, настроении, компании
- Интересуйся жанрами, которые он любит или не любит
- Узнай, в какой обстановке он будет смотреть фильм (один, с друзьями, с семьей, на романтическом свидании)
- Учитывай его текущее настроение
- Сам решай, когда у тебя достаточно информации для качественной рекомендации

РЕЖИМ 2 - ФИНАЛЬНАЯ РЕКОМЕНДАЦИЯ (только JSON):
- Когда ты считаешь, что собрал достаточно информации, переходи в режим рекомендации
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
  "description": "Детальное объяснение, почему именно этот фильм идеально подходит пользователю с учетом всех его предпочтений, настроения и компании"
}

Как определить, что информации достаточно:
- Ты знаешь предпочитаемые жанры или настроение
- Ты понимаешь контекст просмотра (один, с друзьями, с семьей)
- Пользователь дал достаточно деталей для качественной рекомендации
- Обычно 2-4 вопроса достаточно, но можешь задать больше, если чувствуешь, что нужно

Когда начинаешь рекомендацию, подбирай фильм, который действительно соответствует ВСЕМ предпочтениям пользователя.
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5005)

