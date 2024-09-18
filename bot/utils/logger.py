# bot/utils/logger.py
import logging
import os
from datetime import datetime

from aiogram import types
from dotenv import load_dotenv

load_dotenv()
REGISTERED_USERS_DIR = os.getenv('REGISTERED_USERS_DIR')  # Убедись, что переменная окружения загружена

def setup_logger(log_file: str):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )


def get_message_type_log(message: types.Message) -> str:
    """
    Определяет тип сообщения и возвращает строку для логирования.
    """
    if message.text:
        return message.text
    elif message.document:
        return "Отправили файл"
    elif message.photo:
        return "Отправили фото"
    elif message.video:
        return "Отправили видео"
    elif message.audio:
        return "Отправили аудио"
    elif message.sticker:
        return "Отправили стикер"
    else:
        return "Неизвестный тип сообщения"

async def log_chat_history(chat_id: int, message_text: str, sender_type: str):
    """
    Логирует сообщения в файл chat_log.txt в папке пользователя.
    """
    # Проверяем, существует ли директория с именем, начинающимся с chat_id
    user_dirs = [d for d in os.listdir(REGISTERED_USERS_DIR) if d.startswith(str(chat_id))]

    if not user_dirs:
        print(f"Директория для chat_id {chat_id} не найдена. Сообщение // {message_text} // не будет сохранено.")
        return  # Если директория не найдена, ничего не делаем

    # Используем первую найденную директорию, соответствующую chat_id
    user_dir = os.path.join(REGISTERED_USERS_DIR, user_dirs[0])

    # Путь к файлу лога сообщений
    log_file_path = os.path.join(user_dir, "chat_log.txt")

    # Формирование строки для записи
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"{timestamp} {sender_type.capitalize()}: {message_text}\n"

    # Запись сообщения в текстовый файл
    with open(log_file_path, 'a', encoding='utf-8') as log_file:
        log_file.write(log_entry)
