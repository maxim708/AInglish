import json
import os

FILE_NAME = 'users.json'

def load_users():
    """Загружает данные из файла"""
    if not os.path.exists(FILE_NAME):
        # Если файла нет, создаем пустой
        save_users({})
        return {}
    try:
        with open(FILE_NAME, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        # Если файл поврежден, возвращаем пустую базу
        return {}

def save_users(data):
    """Сохраняет данные в файл"""
    with open(FILE_NAME, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Пример использования
users_db = load_users()