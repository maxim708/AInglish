# -*- coding: utf-8 -*-
"""
ИИ-агент AInglish» — Помощник по английскому языку для 6 класса
Проект для фестиваля «Область ИИзменений» (2026)
"""

import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import requests
import json
import os
import random
from random import randint
from config import (
    VK_TOKEN, VK_GROUP_ID, YANDEX_API_KEY, YANDEX_FOLDER_ID,
    SYSTEM_PROMPT, FORBIDDEN_WORDS
)

# ==================== БАЗА ДАННЫХ (users.json) ====================

FILE_NAME = 'users.json'

def load_users():
    """Загружает данные из файла"""
    if not os.path.exists(FILE_NAME):
        save_users({})
        return {}
    try:
        with open(FILE_NAME, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_users(data):
    """Сохраняет данные в файл"""
    with open(FILE_NAME, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def update_user(user_id, **kwargs):
    """Обновляет данные пользователя в профиле"""
    users = load_users()
    user_id = str(user_id)
    if user_id not in users:
        users[user_id] = {
            "level": 1,
            "mistakes": [],
            "last_topic": "Start",
            "messages_count": 0,
            "words_learned": 0
        }
    for key, value in kwargs.items():
        users[user_id][key] = value
    save_users(users)

def get_user_profile(user_id):
    """Получает или создаёт профиль пользователя"""
    users = load_users()
    user_id = str(user_id)
    
    if user_id not in users:
        users[user_id] = {
            "level": 1,
            "mistakes": [],
            "last_topic": "Start",
            "messages_count": 0
        }
        save_users(users)
    
    return users[user_id]

def update_user_progress(user_id, mistake=None, topic=None):
    """Обновляет прогресс пользователя"""
    users = load_users()
    user_id = str(user_id)
    
    if user_id not in users:
        users[user_id] = {"level": 1, "mistakes": [], "last_topic": "Start", "messages_count": 0}
    
    if mistake and mistake not in users[user_id]["mistakes"]:
        users[user_id]["mistakes"].append(mistake)
    
    if topic:
        users[user_id]["last_topic"] = topic
    
    users[user_id]["messages_count"] = users[user_id].get("messages_count", 0) + 1
    save_users(users)

# ==================== ПРОВЕРКА БЕЗОПАСНОСТИ (п.44 Положения) ====================

def check_safety(text):
    """Проверяет текст на запрещённые темы"""
    text_lower = text.lower()
    for word in FORBIDDEN_WORDS:
        if word in text_lower:
            return False
    return True

def get_safe_response():
    """Возвращает безопасный ответ при нарушении правил"""
    return "Let's talk about something more fun! 🌟 How about your hobbies or favorite food? 🍕"

# ==================== YANDEX GPT API ====================

def ask_yandex_gpt(user_message, user_profile):
    """Отправляет запрос к YandexGPT"""
    # Use synchronous endpoint to get completion in one request.
    # The Async endpoint returns an operation id and must be polled separately.
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {YANDEX_API_KEY}"
    }
    
    # Добавляем контекст о пользователе в промпт
    context_prompt = f"""
    {SYSTEM_PROMPT}
    
    ИНФОРМАЦИЯ ОБ УЧЕНИКЕ:
    - Уровень: {user_profile['level']}
    - Частые ошибки: {', '.join(user_profile['mistakes'][:3]) if user_profile['mistakes'] else 'нет'}
    - Последняя тема: {user_profile['last_topic']}
    
    СООБЩЕНИЕ УЧЕНИКА: {user_message}
    """
    
    data = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.7,
            "maxTokens": 500
        },
        "messages": [
            {"role": "system", "text": context_prompt},
            {"role": "user", "text": user_message}
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if 'result' in result and 'alternatives' in result['result']:
            return result['result']['alternatives'][0]['message']['text']
        else:
            return "Sorry, I had a technical issue. Let's try again! 😊"
    
    except requests.HTTPError as e:
        body = ""
        try:
            body = response.text
        except Exception:
            body = "<no body>"
        print(f"Error with Yandex GPT: HTTP {getattr(response, 'status_code', '?')} - {body}")
        print(f"Requests exception: {e}")
        return "Oops! Something went wrong. Please try again later! 🔧"
    except Exception as e:
        print(f"Error with Yandex GPT: {e}")
        return "Oops! Something went wrong. Please try again later! 🔧"

# ==================== VK BOT ====================

def send_message(vk, user_id, message):
    """Отправляет сообщение пользователю ВКонтакте с меню-клавиатурой."""
    vk.messages.send(
        user_id=user_id,
        message=message,
        keyboard=build_main_menu_keyboard(),
        random_id=randint(0, 2**31)
    )

def build_main_menu_keyboard():
    """Клавиатура с основными командами бота (меню)."""
    kb = VkKeyboard(one_time=False, inline=False)
    kb.add_button("🏁 Start", VkKeyboardColor.PRIMARY)
    kb.add_button("ℹ️ Help", VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("📚 Words", VkKeyboardColor.POSITIVE)
    kb.add_button("❓ Quiz", VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button("📖 Grammar", VkKeyboardColor.SECONDARY)
    kb.add_button("📊 Progress", VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("🔄 Reset", VkKeyboardColor.NEGATIVE)
    return kb.get_keyboard()

def send_menu(vk, user_id, text="Выбери команду кнопками ниже 👇"):
    """Отправляет меню команд пользователю."""
    vk.messages.send(
        user_id=user_id,
        message=text,
        keyboard=build_main_menu_keyboard(),
        random_id=randint(0, 2**31)
    )

def process_message(vk, event):
    """Обрабатывает входящее сообщение"""
    user_id = event.user_id
    message_text = event.text
    
    # 1. Проверка безопасности (п.44 Положения)
    if not check_safety(message_text):
        send_message(vk, user_id, get_safe_response())
        update_user_progress(user_id)
        return

    # 1.1. VK "Начать" может приходить как payload (а не как "/start").
    try:
        payload_raw = getattr(event, "message", None)
        if isinstance(payload_raw, dict):
            payload_raw = payload_raw.get("payload")
        if payload_raw:
            payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
            if isinstance(payload, dict) and payload.get("command") == "start":
                message_text = "/start"
    except Exception:
        pass

    # 1.5. Если пользователь просит меню — показываем клавиатуру
    if message_text.strip().lower() in ("/menu", "menu", "меню"):
        send_menu(vk, user_id)
        update_user_progress(user_id)
        return

    # 2. Проверка, является ли сообщение командой (/start, /help, /quiz и т.п.)
    # Кнопки меню отправляют "Start/Help/Words..." — нормализуем в команды.
    normalized_text = message_text.strip()
    lower = normalized_text.lower()
    button_map = {
        "🏁 start": "/start",
        "start": "/start",
        "начать": "/start",
        "начни": "/start",
        "ℹ️ help": "/help",
        "help": "/help",
        "📚 words": "/words",
        "words": "/words",
        "❓ quiz": "/quiz",
        "quiz": "/quiz",
        "📖 grammar": "/grammar",
        "grammar": "/grammar",
        "📊 progress": "/progress",
        "progress": "/progress",
        "🔄 reset": "/reset",
        "reset": "/reset",
    }
    if lower in button_map:
        normalized_text = button_map[lower]

    command_response, is_command = process_command(user_id, normalized_text)
    if is_command:
        # После выполнения команды показываем меню, чтобы пользователь мог дальше выбирать кнопками.
        vk.messages.send(
            user_id=user_id,
            message=command_response,
            keyboard=build_main_menu_keyboard(),
            random_id=randint(0, 2**31)
        )
        update_user_progress(user_id)
        return
    
    # 3. Обычный диалог: получение профиля пользователя
    user_profile = get_user_profile(user_id)
    
    # 4. Запрос к YandexGPT
    ai_response = ask_yandex_gpt(message_text, user_profile)
    
    # 5. Отправка ответа + отдельное сообщение-меню с клавиатурой.
    # В некоторых клиентах VK клавиатура может "сворачиваться" после ввода текста пользователем,
    # поэтому фиксируем показ кнопок отдельным сообщением сразу после ответа.
    vk.messages.send(
        user_id=user_id,
        message=ai_response,
        random_id=randint(0, 2**31)
    )
    send_menu(vk, user_id)
    
    # 6. Обновление прогресса
    update_user_progress(user_id)

def cmd_start(user_id):
    """Команда /start — Приветствие и краткая справка"""
    profile = get_user_profile(user_id)
    return f"""
👋 Привет! Я AInglish — твой помощник по английскому!

📊 Твой текущий уровень: {profile['level']}
💬 Сообщений написано: {profile['messages_count']}

📌 Также доступны команды:
/help — Помощь
/words — Учить слова
/quiz — Викторина
/grammar — Грамматика
/progress — Мой прогресс
"""

def cmd_help(user_id):
    """Команда /help — Список команд"""
    return """
📚 AInglish — Команды:

/start — Приветствие и краткая справка
/help — Эта справка
/words — Мини-игра: учим 5 новых слов 🎮
/quiz — Викторина на проверку знаний ❓
/grammar — Разбор грамматической темы 📖
/progress — Показать твой прогресс 📊
/reset — Сбросить прогресс и начать заново 🔄

💡 Просто пиши на английском — я пойму и помогу!
"""

def cmd_words(user_id):
    """Команда /words — Мини-игра с словами"""
    profile = get_user_profile(user_id)
    
    # Базы слов по уровням
    words_db = {
        1: [
            {"word": "Apple", "translation": "Яблоко", "emoji": "🍎"},
            {"word": "Cat", "translation": "Кошка", "emoji": "🐱"},
            {"word": "Dog", "translation": "Собака", "emoji": "🐕"},
            {"word": "Book", "translation": "Книга", "emoji": "📚"},
            {"word": "School", "translation": "Школа", "emoji": "🏫"}
        ],
        2: [
            {"word": "Beautiful", "translation": "Красивый", "emoji": "✨"},
            {"word": "Friend", "translation": "Друг", "emoji": "👫"},
            {"word": "Family", "translation": "Семья", "emoji": "👨‍👩‍👧"},
            {"word": "Interesting", "translation": "Интересный", "emoji": "🤔"},
            {"word": "Tomorrow", "translation": "Завтра", "emoji": "📅"}
        ],
        3: [
            {"word": "Achievement", "translation": "Достижение", "emoji": "🏆"},
            {"word": "Opportunity", "translation": "Возможность", "emoji": "🚪"},
            {"word": "Knowledge", "translation": "Знание", "emoji": "🧠"},
            {"word": "Experience", "translation": "Опыт", "emoji": "💼"},
            {"word": "Challenge", "translation": "Вызов", "emoji": "⚡"}
        ]
    }
    
    level = profile.get('level', 1)
    words = words_db.get(level, words_db[1])
    selected = random.sample(words, min(3, len(words)))
    
    # Обновляем счётчик выученных слов
    current_words = profile.get('words_learned', 0)
    update_user(user_id, words_learned=current_words + len(selected))
    
    message = "🎮 Мини-игра: Учим новые слова!\n\n"
    for i, word in enumerate(selected, 1):
        message += f"{i}. {word['emoji']} {word['word']} — {word['translation']}\n"
    
    message += "\n💡 Попробуй составить предложение с любым из этих слов!"
    return message

def cmd_quiz(user_id):
    """Команда /quiz — Викторина"""
    profile = get_user_profile(user_id)
    level = profile.get('level', 1)
    
    questions = {
        1: [
            {"q": "Как переводится 'Cat'?", "a": ["🐱 Кошка", "🐕 Собака", "🐦 Птица"], "correct": 0},
            {"q": "Выбери правильный вариант: I ___ a student.", "a": ["am", "is", "are"], "correct": 0},
            {"q": "Как будет 'Школа' по-английски?", "a": ["School", "Shool", "Scool"], "correct": 0}
        ],
        2: [
            {"q": "Прошедшее время от 'go':", "a": ["goed", "went", "gone"], "correct": 1},
            {"q": "Выбери: She ___ to music every day.", "a": ["listen", "listens", "listening"], "correct": 1},
            {"q": "Множественное число от 'child':", "a": ["childs", "children", "childes"], "correct": 1}
        ],
        3: [
            {"q": "Present Perfect от 'write':", "a": ["have wrote", "have written", "had wrote"], "correct": 1},
            {"q": "Выбери синоним 'big':", "a": ["small", "large", "tiny"], "correct": 1},
            {"q": "Антоним слова 'hot':", "a": ["warm", "cold", "cool"], "correct": 1}
        ]
    }
    
    q_list = questions.get(level, questions[1])
    question = random.choice(q_list)
    
    message = f"❓ Викторина (Уровень {level}):\n\n"
    message += f"{question['q']}\n\n"
    for i, answer in enumerate(question['a']):
        message += f"{i + 1}. {answer}\n"
    message += "\nНапиши номер правильного ответа: 1, 2 или 3"
    
    # Сохраняем текущий вопрос в профиль для проверки ответа
    update_user(user_id, current_quiz=question)
    return message

def cmd_grammar(user_id):
    """Команда /grammar — Объяснение грамматики"""
    profile = get_user_profile(user_id)
    level = profile.get('level', 1)
    
    grammar_topics = {
        1: """
📖 Грамматика: Глагол "to be" (быть)

🔹 I am — Я есть
🔹 You are — Ты есть
🔹 He/She/It is — Он/Она/Оно есть

Примеры:
✅ I am a student.
✅ She is my friend.
✅ It is a cat.

Попробуй: "My name ___ Anna." (am/is/are?)
""",
        2: """
📖 Грамматика: Present Simple

Используем для регулярных действий!

🔹 I/You/We/They + глагол (I play)
🔹 He/She/It + глагол + s (She plays)

Примеры:
✅ I play football every day.
✅ She plays piano.

Попробуй: "He ___ (like) apples."
""",
        3: """
📖 Грамматика: Past Simple

Используем для действий в прошлом!

🔹 Правильные глаголы: + ed (play → played)
🔹 Неправильные: запоминаем (go → went)

Примеры:
✅ I played yesterday.
✅ She went to school.

Попробуй: "They ___ (visit) us last week."
"""
    }
    
    return grammar_topics.get(level, grammar_topics[1])

def cmd_progress(user_id):
    """Команда /progress — Показать прогресс"""
    profile = get_user_profile(user_id)
    
    # Расчёт уровня мастерства
    messages = profile.get('messages_count', 0)
    words = profile.get('words_learned', 0)
    
    if messages < 10:
        rank = "🌱 Новичок"
    elif messages < 50:
        rank = "🌿 Ученик"
    elif messages < 100:
        rank = "🌳 Продвинутый"
    else:
        rank = "🏆 Мастер"
    
    return f"""
📊 Твой прогресс в AInglish

👤 Уровень: {profile.get('level', 1)}
💬 Сообщений: {messages}
📚 Слов выучено: {words}
🏅 Ранг: {rank}

⚠️ Частые ошибки: {', '.join(profile.get('mistakes', [])[:3]) or 'нет'}

Продолжай практиковаться! You're doing great! 🌟
"""

def cmd_reset(user_id):
    """Команда /reset — Сброс прогресса"""
    update_user(user_id, level=1, mistakes=[], last_topic="Start", messages_count=0, words_learned=0)
    return """
🔄 Прогресс сброшен!

Ты начинаешь заново. Выбери уровень:
🔹 1 — Только начинаю
🔹 2 — Уже учусь
🔹 3 — Хочу практики

Напиши цифру: 1, 2 или 3
"""

def check_quiz_answer(user_id, answer, question):
    """Проверка ответа на викторину"""
    try:
        answer_num = int(answer) - 1
        if answer_num == question.get('correct', -1):
            update_user(user_id, words_learned=load_users()[str(user_id)].get('words_learned', 0) + 1)
            return "✅ Правильно! Молодец! 🎉 Хочешь ещё вопрос? Напиши /quiz"
        else:
            correct_answer = question['a'][question['correct']]
            return f"❌ Неверно. Правильный ответ: {correct_answer}. Попробуй ещё! /quiz"
    except:
        return "Напиши цифру: 1, 2 или 3."

# ==================== МЕНЕДЖЕР КОМАНД ====================

def process_command(user_id, text):
    """
    Обрабатывает текст команды и возвращает ответ
    Возвращает: (ответ, флаг_это_команда)
    """
    text = text.strip().lower()
    
    # Проверка ответа на викторину (варианты 1/2/3)
    if text in ['1', '2', '3']:
        users = load_users()
        profile = users.get(str(user_id), {})
        current_quiz = profile.get('current_quiz')
        if current_quiz:
            return check_quiz_answer(user_id, text, current_quiz), True
    
    # Обработка команд
    if text == '/start':
        return cmd_start(user_id), True
    elif text == '/help':
        return cmd_help(user_id), True
    elif text == '/words':
        return cmd_words(user_id), True
    elif text == '/quiz':
        return cmd_quiz(user_id), True
    elif text == '/grammar':
        return cmd_grammar(user_id), True
    elif text == '/progress':
        return cmd_progress(user_id), True
    elif text == '/reset':
        return cmd_reset(user_id), True
    
    # Это не команда — обычный диалог
    return None, False
# ==================== ЗАПУСК БОТА ====================

def main():
    """Основная функция запуска бота"""
    print("🤖 AInglish Bot запущен...")
    
    # Авторизация VK
      
   
    # Long Poll для получения сообщений
    
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    
    print("✅ Соединение с VK установлено")
    
    lp = VkLongPoll(vk_session, int(VK_GROUP_ID))
    
    print("✅ Работа с сообщениями...")
    print("🎯 Бот готов! Отправляйте сообщения в свое сообщество VK.")
    
    for event in lp.listen():
        if event.type == vk_api.longpoll.VkEventType.MESSAGE_NEW:
            if event.to_me and event.text:
                print(f"📩 Сообщение от пользователя {event.user_id}: {event.text[:50]}...")
                process_message(vk, event)
                print(f"✅ Ответ пользователю {event.user_id}")

if __name__ == '__main__':
    main()