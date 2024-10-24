# bot/handlers/cleanup.py

import os
from datetime import datetime

from aiogram import types

from bot.utils.logger import get_message_type_log, log_chat_history

REGISTERED_USERS_DIR = os.getenv('REGISTERED_USERS_DIR')
# Хранилище для сообщений и их типов
user_messages = {}
important_messages = {}
message_types_mapping = {}  # Добавляем новый словарь для маппинга типов сообщений
share_message_types_mapping = {}  # Логика для маппинга типов сообщений для функции "Поделиться с другом"

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
    await log_chat_history(chat_id, message_text, sender_type)
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
    print(f"Stored message: {message_text} (ID: {chat_id}, Sender: {sender_type})")


# === Новая логика для маппинга типов сообщений ===
async def register_message_type(chat_id: int, message_id: int, message_type: str, bot):
    """
    Регистрируем новый тип сообщения для конкретного чата и сохраняем его.
    """

    if chat_id not in message_types_mapping:
        message_types_mapping[chat_id] = {}

    # Если для данного типа уже есть сообщение, удаляем его
    if message_type in message_types_mapping[chat_id]:
        old_message_id = message_types_mapping[chat_id][message_type]

        try:
            # Фактическое удаление старого сообщения через Telegram API
            await bot.delete_message(chat_id, old_message_id)
        except Exception as e:
            print(f"Ошибка при удалении старого сообщения {old_message_id}: {e}")

        # Убираем сообщение из списка важных
        try:
            important_messages[chat_id].remove(old_message_id)
        except KeyError:
            pass  # Если сообщение уже удалено, игнорируем

    # Сохраняем новое сообщение по типу
    message_types_mapping[chat_id][message_type] = message_id

    # Добавляем новое сообщение в список важных сообщений
    if chat_id not in important_messages:
        important_messages[chat_id] = set()

    important_messages[chat_id].add(message_id)
    print(important_messages[chat_id])


async def store_important_message(bot, chat_id: int, message_id: int, message: types.Message = None,
                                  message_type: str = None):
    """
    Сохраняет ID важного сообщения для конкретного чата.
    Если новое важное сообщение добавляется, старое удаляется.
    """
    if message:
        log_text = get_message_type_log(message)
        await log_chat_history(chat_id, log_text, "bot")

    if chat_id not in important_messages:
        important_messages[chat_id] = set()

    # Если это сообщение с файлом, удалим старые сообщения с тем же типом
    if message_type in message_types_mapping.get(chat_id, {}):
        old_message_id = message_types_mapping[chat_id][message_type]
        try:
            await bot.delete_message(chat_id, old_message_id)
        except Exception as e:
            print(f"Не удалось удалить старое важное сообщение {old_message_id}: {e}")

    important_messages[chat_id].add(message_id)

    # Регистрируем тип сообщения (например, файл или QR-код)
    if message_type:
        await register_message_type(chat_id, message_id, message_type, 'bot')


# Функция удаления неважных сообщений. Не трогаем сообщения с кнопками.
async def delete_unimportant_messages(chat_id: int, bot):
    """
    Удаляет все сообщения в чате, кроме важных.
    """
    if chat_id not in important_messages:
        important_messages[chat_id] = set()

    if chat_id not in user_messages:
        # Если нет сообщений в данном чате, просто выходим
        return

    # Получаем список сообщений для удаления, кроме сообщений с текстом и кнопками
    messages_to_delete = [
        message_id for message_id, _, _ in user_messages[chat_id]
        if message_id not in important_messages[chat_id] and message_id not in message_types_mapping.get(chat_id,
                                                                                                         {}).values()
    ]

    # Удаляем сообщения
    for message_id in messages_to_delete:
        try:
            await bot.delete_message(chat_id, message_id)
        except Exception as e:
            print(f"Не удалось удалить сообщение {message_id}: {e}")

    # Очищаем user_messages, так как все неважные сообщения удалены
    user_messages[chat_id] = [
        (message_id, message_text, sender_type)
        for message_id, message_text, sender_type in user_messages[chat_id]
        if message_id in important_messages[chat_id]
    ]


# async def log_chat_history(chat_id: int, message_text:str,sender_type:str):
#     # Проверяем, существует ли директория с именем, начинающимся с chat_id
#     user_dirs = [d for d in os.listdir(REGISTERED_USERS_DIR) if d.startswith(str(chat_id))]
#
#     if not user_dirs:
#         print(f"Директория для chat_id {chat_id} не найдена. Сообщение // {message_text} // не будет сохранено.")
#         return  # Если директория не найдена, ничего не делаем
#
#     # Используем первую найденную директорию, соответствующую chat_id
#     user_dir = os.path.join(REGISTERED_USERS_DIR, user_dirs[0])
#
#     # Путь к файлу лога сообщений
#     log_file_path = os.path.join(user_dir, "chat_log.txt")
#
#     # Формирование строки для записи
#     timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#     if sender_type == 'user':
#         log_entry = f"{timestamp} User: {message_text}\n"
#     else:
#         log_entry = f"{timestamp} Bot: {message_text}\n"
#
#     # Запись сообщения в текстовый файл
#     with open(log_file_path, 'a', encoding='utf-8') as log_file:
#         log_file.write(log_entry)


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

    # старая логика
    # async def store_important_message(chat_id: int, message_id: int, message: types.Message = None,):
    #     """
    #     Сохраняет ID важного сообщения для конкретного чата на основе определенных критериев.
    #     """
    #     await log_chat_history(chat_id, message.text, "bot")
    #     if chat_id not in important_messages:
    #         important_messages[chat_id] = set()  # используем множество для предотвращения дубликатов
    #
    #     # Критерии для определения важности сообщения
    #     if message and message.message_id not in important_messages[chat_id]:
    #
    #         # Сообщения, содержащие файлы конфигурации или изображения
    #         if message.document or message.photo:
    #
    #             important_messages[chat_id].add(message_id)
    #         # Сообщение приветствия (проверяем часть строки)
    #         elif "👋 Всем привет!" in message.text:
    #
    #             important_messages[chat_id].add(message_id)
    #         # Сообщение с инструкцией (проверяем часть строки в нижнем регистре)
    #         elif "добро пожаловать!" in message.text.lower() or "ого, вы уже в игре!" in message.text.lower():
    #             important_messages[chat_id].add(message_id)
    #
    #         elif "/start" in message.text in message.text.lower():
    #             important_messages[chat_id].add(message_id)
    #
    #     # Если сообщение не передано, не добавляем его как важное по умолчанию
    #     # important_messages[chat_id].add(message_id)
    #

    # старая логика
    # async def store_important_message(chat_id: int, message_id: int, message: types.Message = None,):
    #     """
    #     Сохраняет ID важного сообщения для конкретного чата на основе определенных критериев.
    #     """
    #     await log_chat_history(chat_id, message.text, "bot")
    #     if chat_id not in important_messages:
    #         important_messages[chat_id] = set()  # используем множество для предотвращения дубликатов
    #
    #     # Критерии для определения важности сообщения
    #     if message and message.message_id not in important_messages[chat_id]:
    #
    #         # Сообщения, содержащие файлы конфигурации или изображения
    #         if message.document or message.photo:
    #
    #             important_messages[chat_id].add(message_id)
    #         # Сообщение приветствия (проверяем часть строки)
    #         elif "👋 Всем привет!" in message.text:
    #
    #             important_messages[chat_id].add(message_id)
    #         # Сообщение с инструкцией (проверяем часть строки в нижнем регистре)
    #         elif "добро пожаловать!" in message.text.lower() or "ого, вы уже в игре!" in message.text.lower():
    #             important_messages[chat_id].add(message_id)
    #
    #         elif "/start" in message.text in message.text.lower():
    #             important_messages[chat_id].add(message_id)
    #
    #     # Если сообщение не передано, не добавляем его как важное по умолчанию
    #     # important_messages[chat_id].add(message_id)
    #


async def delete_important_message(chat_id, message_type, bot):
    """
    Удаляет важное сообщение по типу.
    :param chat_id: ID чата пользователя
    :param message_type: Тип сообщения (например, 'subscription_check' или 'file_choice')
    :param bot: объект бота
    """

    if chat_id in message_types_mapping and message_type in message_types_mapping[chat_id]:
        message_id = message_types_mapping[chat_id][message_type]

        try:
            # Удаляем сообщение из чата
            await bot.delete_message(chat_id, message_id)
            # Удаляем сообщение из маппинга важных сообщений
            important_messages[chat_id].remove(message_id)
            del message_types_mapping[chat_id][message_type]
        except Exception as e:
            print(f"Не удалось удалить сообщение {message_id}: {e}")


async def delete_message_with_type(chat_id: int, message_type: str, bot):
    """
    Удаляет сообщение определенного типа для конкретного чата.

    Параметры:
    - chat_id: идентификатор чата (целое число).
    - message_type: тип сообщения, которое нужно удалить (строка).
    - bot: объект бота, используемый для взаимодействия с Telegram API.
    """
    # Приводим chat_id к целому числу на случай, если он передан как строка.
    chat_id = int(chat_id)

    # Проверяем, существует ли маппинг для данного чата в message_types_mapping.
    # Это необходимо, чтобы убедиться, что в данном чате зарегистрированы сообщения.
    if chat_id in message_types_mapping:
        # Проверяем, зарегистрирован ли указанный тип сообщения для данного чата.
        if message_type in message_types_mapping[chat_id]:
            # Получаем ID сообщения, которое нужно удалить, и удаляем запись из маппинга.
            message_id = message_types_mapping[chat_id].pop(message_type)

            # Пытаемся удалить сообщение через Telegram API.
            # Это важно, чтобы очистить старое сообщение из чата, когда приходит новое.
            try:
                await bot.delete_message(chat_id, message_id)
            except Exception as e:
                # Если возникает ошибка при удалении, она будет проигнорирована,
                # но важно понимать, что сообщение может остаться в чате.
                print(f"[ERROR] Ошибка при удалении сообщения с ID {message_id}: {e}")

            # Убираем сообщение из списка важных сообщений для данного чата.
            # Это делается, чтобы поддерживать актуальный список важных сообщений.
            try:
                if chat_id in important_messages and message_id in important_messages[chat_id]:
                    important_messages[chat_id].remove(message_id)
            except KeyError:
                # Если сообщение не найдено в списке важных, это не проблема, продолжаем работу.
                pass
        # Если тип сообщения не найден, это означает, что данное сообщение не зарегистрировано.
    # Если чата нет в маппинге, значит для этого чата нет сохраненных сообщений.
