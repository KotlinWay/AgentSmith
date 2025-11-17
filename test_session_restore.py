"""
Тест восстановления истории диалога после перезапуска (День 9)
"""
from memory_service import MemoryService
import uuid

def test_session_restore():
    """Демонстрирует восстановление сессии"""
    print("🧪 ТЕСТ ВОССТАНОВЛЕНИЯ ИСТОРИИ ДИАЛОГА")
    print("=" * 60)

    memory = MemoryService("test_session_restore.db")

    # Шаг 1: Создаем сессию и добавляем сообщения
    print("\n1️⃣ Создаем новую сессию и добавляем сообщения...")
    session_id = str(uuid.uuid4())
    memory.create_session(session_id, "Тестовая сессия для восстановления")

    # Добавляем несколько сообщений
    messages_to_save = [
        ("user", "Привет! Как дела?", 5),
        ("assistant", "Привет! Отлично, спасибо!", 6),
        ("user", "[Рассуждение] Решить задачу про овец", 8),
        ("assistant", "[Рассуждение] Метод: step_by_step, Результаты получены", 10),
        ("user", "[Рекомендация] Посоветуй фильм", 5),
        ("assistant", "[Рекомендация] Конечно! Какой жанр...", 7),
        ("user", "Что ты умеешь?", 4),
        ("assistant", "Я могу помочь с разными задачами!", 8),
    ]

    for role, content, tokens in messages_to_save:
        memory.save_message(session_id, role, content, tokens)

    print(f"   ✅ Сохранено {len(messages_to_save)} сообщений")
    print(f"   📝 Session ID: {session_id[:12]}...")

    # Шаг 2: Симулируем "перезапуск" - создаем новый экземпляр
    print("\n2️⃣ Симулируем перезапуск приложения...")
    print("   🔄 Создаем новый экземпляр сервиса памяти...")
    memory2 = MemoryService("test_session_restore.db")

    # Шаг 3: Загружаем последнюю сессию (как это делает приложение)
    print("\n3️⃣ Загружаем последнюю сессию из БД...")
    sessions = memory2.list_sessions(limit=1)

    if sessions:
        loaded_session_id = sessions[0]['session_id']
        print(f"   ✅ Найдена сессия: {sessions[0]['title']}")
        print(f"   📝 Session ID: {loaded_session_id[:12]}...")
        print(f"   ✔️  IDs совпадают: {loaded_session_id == session_id}")
    else:
        print("   ❌ Сессия не найдена!")
        return False

    # Шаг 4: Восстанавливаем историю
    print("\n4️⃣ Восстанавливаем историю сообщений...")
    messages = memory2.get_messages(loaded_session_id, limit=50)

    print(f"   ✅ Загружено {len(messages)} сообщений")

    # Разделяем по типам (как в приложении)
    chat_messages = []
    recommendation_messages = []
    reasoning_messages = []

    for msg in messages:
        content = msg['content']
        if content.startswith('[Рассуждение]'):
            reasoning_messages.append(msg)
        elif content.startswith('[Рекомендация]'):
            recommendation_messages.append(msg)
        else:
            chat_messages.append(msg)

    print(f"\n   Разделение по режимам:")
    print(f"   💬 Обычный чат: {len(chat_messages)} сообщений")
    print(f"   🎯 Рекомендации: {len(recommendation_messages)} сообщений")
    print(f"   🧠 Рассуждения: {len(reasoning_messages)} сообщений")

    # Показываем восстановленную историю чата
    print(f"\n   📜 Восстановленная история обычного чата:")
    for msg in chat_messages:
        role_icon = "👤" if msg['role'] == 'user' else "🤖"
        print(f"      {role_icon} {msg['role']}: {msg['content'][:50]}...")

    # Шаг 5: Проверка
    print("\n5️⃣ Проверка корректности восстановления...")
    expected_chat = 4  # Должно быть 4 обычных сообщения
    expected_reasoning = 2  # Должно быть 2 сообщения рассуждений
    expected_recommendation = 2  # Должно быть 2 сообщения рекомендаций

    all_ok = True
    if len(chat_messages) == expected_chat:
        print(f"   ✅ Обычный чат: {len(chat_messages)} сообщений (ожидалось {expected_chat})")
    else:
        print(f"   ❌ Обычный чат: {len(chat_messages)} сообщений (ожидалось {expected_chat})")
        all_ok = False

    if len(reasoning_messages) == expected_reasoning:
        print(f"   ✅ Рассуждения: {len(reasoning_messages)} сообщений (ожидалось {expected_reasoning})")
    else:
        print(f"   ❌ Рассуждения: {len(reasoning_messages)} сообщений (ожидалось {expected_reasoning})")
        all_ok = False

    if len(recommendation_messages) == expected_recommendation:
        print(f"   ✅ Рекомендации: {len(recommendation_messages)} сообщений (ожидалось {expected_recommendation})")
    else:
        print(f"   ❌ Рекомендации: {len(recommendation_messages)} сообщений (ожидалось {expected_recommendation})")
        all_ok = False

    # Очистка
    print("\n6️⃣ Очистка тестовых данных...")
    memory2.delete_session(session_id)
    print("   ✅ Тестовая сессия удалена")

    print("\n" + "=" * 60)
    if all_ok:
        print("🎉 ТЕСТ ПРОЙДЕН УСПЕШНО!")
        print("=" * 60)
        print("\n💡 Выводы:")
        print("   ✅ Сессия корректно сохраняется в БД")
        print("   ✅ История восстанавливается после 'перезапуска'")
        print("   ✅ Сообщения правильно разделяются по режимам")
        print("   ✅ Персистентность работает!")
        return True
    else:
        print("❌ ТЕСТ ПРОВАЛЕН!")
        print("=" * 60)
        return False


if __name__ == "__main__":
    try:
        success = test_session_restore()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ОШИБКА ТЕСТА: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
