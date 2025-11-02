# AgentSmith

Веб-приложение для общения с AI-агентом на базе Yandex GPT. Приложение представляет собой чат-интерфейс с критиком фильмов.

## Требования

- Python 3.7+
- API-ключ Yandex Cloud
- Catalog ID в Yandex Cloud

## Установка

1. Клонируй репозиторий:
```bash
git clone <repository-url>
cd AgentSmith
```

2. Создай виртуальное окружение:
```bash
python3 -m venv venv
source venv/bin/activate  # для macOS/Linux
# или
venv\Scripts\activate  # для Windows
```

3. Установи зависимости:
```bash
pip install -r requirements.txt
```

4. Создай файл конфигурации:
```bash
cp config.example.json config.json
```

5. Открой `config.json` и заполни своими данными:
```json
{
  "api_key": "YOUR_API_KEY_HERE",
  "catalog_id": "YOUR_CATALOG_ID_HERE"
}
```

## Запуск

```bash
python app.py
```

Приложение будет доступно по адресу: `http://localhost:5005`

## Структура проекта

```
AgentSmith/
├── app.py                 # Основной файл Flask приложения
├── requirements.txt       # Зависимости Python
├── config.json           # Конфигурация (не в git)
├── config.example.json   # Шаблон конфигурации
├── templates/
│   └── index.html        # HTML шаблон
└── static/
    ├── style.css         # Стили
    └── script.js         # JavaScript клиент
```

## API Endpoints

- `GET /` - Главная страница с чатом
- `POST /chat` - Отправка сообщения в чат
- `POST /clear` - Очистка истории диалога

## Безопасность

⚠️ **Важно**: Файл `config.json` с секретными данными добавлен в `.gitignore` и не попадает в репозиторий. Никогда не коммить файл с реальными API-ключами!

## Лицензия

MIT

