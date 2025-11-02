from flask import Flask, render_template, request, jsonify
import requests
import json
import os

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


def get_agent_response(user_message):
    """Получает ответ от Yandex GPT агента"""
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {config['api_key']}"
    }
    
    # Формируем историю сообщений
    messages = [
        {
            "role": "system",
            "text": "Ты искушенный критик фильмов"
        }
    ]
    
    # Добавляем историю диалога
    for msg in chat_history[-10:]:  # Берем последние 10 сообщений
        messages.append(msg)
    
    # Добавляем новое сообщение пользователя
    messages.append({
        "role": "user",
        "text": user_message
    })
    
    prompt = {
        "modelUri": f"gpt://{config['catalog_id']}/yandexgpt-lite/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": "2000"
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
            return assistant_text
        else:
            return "Ошибка: неожиданный формат ответа от API"
            
    except requests.exceptions.RequestException as e:
        return f"Ошибка при запросе к API: {str(e)}"
    except Exception as e:
        return f"Ошибка: {str(e)}"


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


@app.route('/clear', methods=['POST'])
def clear_history():
    """Очистка истории чата"""
    global chat_history
    chat_history = []
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5005)

