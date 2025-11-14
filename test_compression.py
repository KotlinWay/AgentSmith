#!/usr/bin/env python3
"""
Тестовый скрипт для демонстрации работы механизма сжатия истории диалога.
День 8: Сжатие диалога
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:5005"


def send_message(message: str, action: str = "send") -> Dict[str, Any]:
    """Отправка сообщения в режиме компрессии"""
    response = requests.post(
        f"{BASE_URL}/compression_test",
        json={"message": message, "action": action}
    )
    return response.json()


def compare_compression(message: str) -> Dict[str, Any]:
    """Сравнение работы с компрессией и без"""
    response = requests.post(
        f"{BASE_URL}/compression_test",
        json={"message": message, "action": "compare"}
    )
    return response.json()


def get_stats() -> Dict[str, Any]:
    """Получение статистики"""
    response = requests.post(
        f"{BASE_URL}/compression_test",
        json={"action": "stats"}
    )
    return response.json()


def clear_history():
    """Очистка истории"""
    response = requests.post(
        f"{BASE_URL}/compression_test",
        json={"action": "clear"}
    )
    return response.json()


def print_separator():
    print("\n" + "=" * 80 + "\n")


def test_compression_mechanism():
    """
    Основной тест механизма компрессии.
    Отправляет серию сообщений и сравнивает результаты.
    """
    print("🔥 ТЕСТ МЕХАНИЗМА СЖАТИЯ ИСТОРИИ ДИАЛОГА (День 8)")
    print_separator()

    # Очистка истории перед началом
    print("Очистка истории...")
    clear_history()

    # Серия тестовых сообщений для создания длинной истории
    test_messages = [
        "Привет! Расскажи мне о космосе.",
        "Что такое черная дыра?",
        "Сколько планет в Солнечной системе?",
        "Расскажи о Марсе подробнее.",
        "Какая температура на поверхности Марса?",
        "Есть ли жизнь на Марсе?",
        "Что такое экзопланеты?",
        "Сколько экзопланет мы нашли?",
        "Что такое зона обитаемости?",
        "Как ищут внеземную жизнь?",
        "Расскажи о программе SETI.",
        "Что такое парадокс Ферми?"
    ]

    print(f"📝 Отправка {len(test_messages)} сообщений для заполнения истории...\n")

    # Отправляем сообщения и собираем метрики
    total_tokens = 0
    total_cost = 0

    for i, message in enumerate(test_messages, 1):
        print(f"[{i}/{len(test_messages)}] Отправка: {message[:50]}...")

        result = send_message(message)

        if result.get('status') == 'ok':
            metrics = result.get('metrics', {})
            stats = result.get('compression_stats', {})

            total_tokens += metrics.get('total_tokens', 0)
            total_cost += metrics.get('cost_rub', 0)

            print(f"   ⏱️  Время: {metrics.get('response_time', 0)}s")
            print(f"   📊 Токены: {metrics.get('input_tokens', 0)} вход + {metrics.get('output_tokens', 0)} выход = {metrics.get('total_tokens', 0)}")
            print(f"   💰 Стоимость: {metrics.get('cost_rub', 0)}₽")

            if stats.get('compression_count', 0) > 0:
                print(f"   🗜️  КОМПРЕССИЯ: Выполнено {stats['compression_count']} раз(а), сэкономлено {stats['total_tokens_saved']} токенов")

            print()

            # Небольшая пауза между запросами
            time.sleep(0.5)
        else:
            print(f"   ❌ Ошибка: {result.get('error')}")
            print()

    print_separator()
    print("📊 ОБЩАЯ СТАТИСТИКА")
    print_separator()

    # Получаем финальную статистику
    stats_result = get_stats()
    if stats_result.get('status') == 'ok':
        stats = stats_result.get('stats', {})

        print(f"Всего сообщений в истории: {stats.get('total_messages', 0)}")
        print(f"Сообщений после компрессии: {stats.get('compressed_messages', 0)}")
        print(f"Компрессий выполнено: {stats.get('compression_count', 0)}")
        print(f"Текущие токены (полная история): {stats.get('current_full_tokens', 0)}")
        print(f"Текущие токены (сжатая история): {stats.get('current_compressed_tokens', 0)}")
        print(f"Степень сжатия: {stats.get('compression_ratio', 0)}%")
        print(f"Всего сэкономлено токенов: {stats.get('total_tokens_saved', 0)}")

    print(f"\nОбщие затраты:")
    print(f"Всего токенов использовано: {total_tokens}")
    print(f"Общая стоимость: {total_cost:.4f}₽")

    print_separator()
    print("🔬 СРАВНИТЕЛЬНЫЙ ТЕСТ: С КОМПРЕССИЕЙ vs БЕЗ КОМПРЕССИИ")
    print_separator()

    # Тестовое сообщение для сравнения
    test_question = "Какие есть теории о будущем Вселенной?"
    print(f"Вопрос для сравнения: {test_question}\n")

    # Выполняем сравнение
    comparison_result = compare_compression(test_question)

    if comparison_result.get('status') == 'ok':
        comp = comparison_result['comparison']

        print("✅ С КОМПРЕССИЕЙ:")
        print(f"   📊 Входные токены: {comp['with_compression']['metrics']['input_tokens']}")
        print(f"   📊 Выходные токены: {comp['with_compression']['metrics']['output_tokens']}")
        print(f"   📊 Всего токенов: {comp['with_compression']['metrics']['total_tokens']}")
        print(f"   💰 Стоимость: {comp['with_compression']['metrics']['cost_rub']}₽")
        print(f"   ⏱️  Время: {comp['with_compression']['metrics']['response_time']}s")
        print(f"   📝 Сообщений в истории: {comp['with_compression']['metrics']['history_messages']}")
        print(f"   📄 Ответ: {comp['with_compression']['response'][:100]}...\n")

        print("❌ БЕЗ КОМПРЕССИИ:")
        print(f"   📊 Входные токены: {comp['without_compression']['metrics']['input_tokens']}")
        print(f"   📊 Выходные токены: {comp['without_compression']['metrics']['output_tokens']}")
        print(f"   📊 Всего токенов: {comp['without_compression']['metrics']['total_tokens']}")
        print(f"   💰 Стоимость: {comp['without_compression']['metrics']['cost_rub']}₽")
        print(f"   ⏱️  Время: {comp['without_compression']['metrics']['response_time']}s")
        print(f"   📝 Сообщений в истории: {comp['without_compression']['metrics']['history_messages']}")
        print(f"   📄 Ответ: {comp['without_compression']['response'][:100]}...\n")

        print("💡 ЭКОНОМИЯ:")
        savings = comp['savings']
        print(f"   📊 Сэкономлено токенов: {savings['tokens_saved']} ({savings['tokens_saved_percent']}%)")
        print(f"   💰 Сэкономлено денег: {savings['cost_saved']}₽ ({savings['cost_saved_percent']}%)")
        print(f"   ⏱️  Разница во времени: {savings['time_difference']}s")

    print_separator()
    print("✅ ТЕСТ ЗАВЕРШЕН!")
    print_separator()


def test_simple_comparison():
    """
    Упрощенный тест для быстрой проверки.
    """
    print("🔥 УПРОЩЕННЫЙ ТЕСТ СЖАТИЯ")
    print_separator()

    # Очистка
    clear_history()

    # Несколько сообщений для создания истории
    messages = [
        "Расскажи о Python",
        "Что такое Django?",
        "Как работает Flask?",
        "Что такое FastAPI?",
        "Сравни Django и Flask",
    ]

    print("Отправка сообщений...")
    for msg in messages:
        result = send_message(msg)
        if result.get('status') == 'ok':
            print(f"✓ {msg[:40]}... - {result['metrics']['total_tokens']} токенов")

    print("\nСравнение работы с компрессией и без:")
    result = compare_compression("Какой фреймворк лучше выбрать?")

    if result.get('status') == 'ok':
        savings = result['comparison']['savings']
        print(f"\n💡 Экономия:")
        print(f"   Токены: {savings['tokens_saved']} ({savings['tokens_saved_percent']}%)")
        print(f"   Стоимость: {savings['cost_saved']}₽ ({savings['cost_saved_percent']}%)")


if __name__ == "__main__":
    try:
        # Проверка доступности сервера
        response = requests.get(BASE_URL)
        if response.status_code == 200:
            print("✅ Сервер доступен\n")

        # Запуск полного теста
        test_compression_mechanism()

        # Можно раскомментировать для упрощенного теста
        # test_simple_comparison()

    except requests.exceptions.ConnectionError:
        print("❌ Ошибка: Не удается подключиться к серверу")
        print("Убедитесь, что Flask приложение запущено на http://localhost:5005")
    except KeyboardInterrupt:
        print("\n\n⚠️ Тест прерван пользователем")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
