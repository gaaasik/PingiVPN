# bot/handlers/cleanup.py

import os
from datetime import datetime

from aiogram import types

from data.text_messages import REGISTERED_USERS_DIR

# Хранилище для сообщений и их типов
user_messages = {}
important_messages = {}
# Дополнительное хранилище для сообщений для базы данных
messages_for_db = []  # Список или используйте другую структуру данных по мере необходимости

async def store_message(chat_id: int, message_id: int, message_text: str, sender_type: str):
    """
    Сохраняет ID сообщения и его текст для конкретного чата, а также информацию о том, кто отправил сообщение.

    :param chat_id: ID чата
    :param message_id: ID сообщения
    :param message_text: Текст сообщения
    :param sender_type: Тип отправителя ('user' или 'bot')
    """
    await log_chat_history(chat_id,message_text,sender_type)
    # Сохраняем сообщение в памяти
    if chat_id not in user_messages:
        user_messages[chat_id] = []

    # Сохраняем сообщение как кортеж (message_id, message_text, sender_type)
    user_messages[chat_id].append((message_id, message_text, sender_type))

    # Добавляем информацию о сообщении в список для базы данных
    messages_for_db.append({
        'chat_id': chat_id,
        'message_id': message_id,
        'message_text': message_text,
        'sender_type': sender_type
    })

    # Выводим сообщение в консоль (или другой логгер), чтобы увидеть, что было сохранено
    print(f"Stored message: {message_text} (ID: {message_id}, Sender: {sender_type})")

async def store_important_message(chat_id: int, message_id: int, message: types.Message = None,):
    """
    Сохраняет ID важного сообщения для конкретного чата на основе определенных критериев.
    """
    await log_chat_history(chat_id, message.text, "bot")
    if chat_id not in important_messages:
        important_messages[chat_id] = set()  # используем множество для предотвращения дубликатов

    # Критерии для определения важности сообщения
    if message and message.message_id not in important_messages[chat_id]:

        # Сообщения, содержащие файлы конфигурации или изображения
        if message.document or message.photo:

            important_messages[chat_id].add(message_id)
        # Сообщение приветствия (проверяем часть строки)
        elif "👋 Всем привет!" in message.text:

            important_messages[chat_id].add(message_id)
        # Сообщение с инструкцией (проверяем часть строки в нижнем регистре)
        elif "добро пожаловать!" in message.text.lower() or "ого, вы уже в игре!" in message.text.lower():
            important_messages[chat_id].add(message_id)

        elif "/start" in message.text in message.text.lower():
            important_messages[chat_id].add(message_id)

    # Если сообщение не передано, не добавляем его как важное по умолчанию
    # important_messages[chat_id].add(message_id)

# bot/handlers/cleanup.py

async def delete_unimportant_messages(chat_id: int, bot):
    """
    Удаляет все сообщения в чате, кроме важных.
    """
    if chat_id not in important_messages:
        important_messages[chat_id] = set()

    if chat_id not in user_messages:
        # Если нет сообщений в данном чате, просто выходим
        return

    # Получаем список сообщений для удаления
    messages_to_delete = [
        message_id for message_id, _, _ in user_messages[chat_id][:-2]
        if message_id not in important_messages[chat_id]
    ]

    # Удаляем сообщения
    for message_id in messages_to_delete:
        try:
            await bot.delete_message(chat_id, message_id)
        except Exception as e:
            print(f"Не удалось удалить сообщение {message_id}: {e}")

    # Оставляем только последние два сообщения в user_messages
    user_messages[chat_id] = user_messages[chat_id][-2:]


async def log_chat_history(chat_id: int, message_text:str,sender_type:str):
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
    if sender_type == 'user':
        log_entry = f"{timestamp} User: {message_text}\n"
    else:
        log_entry = f"{timestamp} Bot: {message_text}\n"

    # Запись сообщения в текстовый файл
    with open(log_file_path, 'a', encoding='utf-8') as log_file:
        log_file.write(log_entry)


async def clear_chat_history(chat_id: int, bot):
    """
    Очищает всю историю чата, удаляя все сообщения.
    """
    # Проверяем, существует ли chat_id в user_messages и important_messages
    if chat_id not in user_messages:
        user_messages[chat_id] = []  # Инициализируем пустой список, если chat_id отсутствует
    if chat_id not in important_messages:
        important_messages[chat_id] = set()  # Инициализируем пустое множество, если chat_id отсутствует

    # Получаем все сообщения, которые нужно удалить
    messages_to_delete = [message_id for message_id, _, _ in user_messages[chat_id]] + list(important_messages[chat_id])

    # Удаляем все сообщения
    for message_id in messages_to_delete:
        try:
            await bot.delete_message(chat_id, message_id)
        except Exception as e:
            print(f"Не удалось удалить сообщение {message_id}: {e}")

    # Очищаем хранилище сообщений для чата
    user_messages[chat_id].clear()
    important_messages[chat_id].clear()  # Также очищаем важные сообщения
    messages_for_db.clear()  # Очищаем сообщения для базы данных