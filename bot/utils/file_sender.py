# Это файл file_sender.py

import os
import shutil
from aiogram.types import FSInputFile

from bot.handlers.cleanup import store_important_message
from data.text_messages import android_instructions, iphone_instructions, mac_instructions, linux_instructions, windows_instructions
from dotenv import load_dotenv

# Загрузка переменных окружения из .env
load_dotenv()
CONFIGS_DIR = os.getenv('CONFIGS_DIR')
BASE_CONFIGS_DIR = os.path.join(CONFIGS_DIR, 'base_configs')
REGISTERED_USERS_DIR = os.path.join(CONFIGS_DIR, 'registered_user')

# Отправка инструкций по устройству
async def send_files_by_device(message, chat_id, device):
    if device == 'android':
        await message.answer(android_instructions)
    elif device == 'iphone':
        await message.answer(iphone_instructions)
    elif device == 'mac':
        await message.answer(mac_instructions)
    elif device == 'linux':
        await message.answer(linux_instructions)
    elif device == 'windows':
        await message.answer(windows_instructions)

    # Путь к общему конфигурационному файлу для всех устройств
    config_file_path = os.path.join(BASE_CONFIGS_DIR, "vpn_config.conf")
    if os.path.exists(config_file_path):
        await message.answer_document(FSInputFile(config_file_path))
    else:
        await message.answer("Конфигурационный файл не найден. Пожалуйста, свяжитесь с поддержкой.")


async def send_config_file(callback_query):
    """
    Отправка конфигурационного файла пользователю через Telegram.
    """
    chat_id = callback_query.message.chat.id
    username = callback_query.from_user.username or 'unknown'
    folder_name = f"{chat_id}_{username}"
    user_dir = os.path.join(REGISTERED_USERS_DIR, folder_name)

    # Путь к конфигурационному файлу
    config_file_path = os.path.join(user_dir, "PingiVPN.conf")

    # Вызов функции создания файлов, если они не найдены
    await create_user_files(chat_id, username)
    # Проверяем, существует ли файл перед отправкой
    if os.path.exists(config_file_path):
        # Отправляем конфигурационный файл пользователю
        message = await callback_query.message.answer_document(FSInputFile(config_file_path))
        return message
    else:
        # Если файл не найден, возвращаем None
        return await callback_query.message.answer("Конфигурационный файл не найден.")


async def send_qr_code(callback_query):
    """
    Отправка QR-кода пользователю через Telegram.
    """
    chat_id = callback_query.message.chat.id
    username = callback_query.from_user.username or 'unknown'
    folder_name = f"{chat_id}_{username}"
    user_dir = os.path.join(REGISTERED_USERS_DIR, folder_name)

    # Путь к изображению с QR-кодом
    qr_code_path = os.path.join(user_dir, "PingiVPN.png")
    # Вызов функции создания файлов, если они не найдены
    await create_user_files(chat_id, username)
    # Проверяем, существует ли файл перед отправкой
    if os.path.exists(qr_code_path):
        # Отправляем QR-код пользователю
        message = await callback_query.message.answer_photo(FSInputFile(qr_code_path))
        return message
    else:
        # Если файл не найден, возвращаем None
        return await callback_query.message.answer("QR-код не найден.")

# Функция для создания файлов пользователя
async def create_user_files(chat_id, username):
    try:
        folder_name = f"{chat_id}_{username}"
        user_dir = os.path.join(REGISTERED_USERS_DIR, folder_name)

        # Проверяем, существует ли директория пользователя
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)

        # Проверяем, существуют ли уже необходимые файлы
        config_file_path = os.path.join(user_dir, 'PingiVPN.conf')
        qr_code_path = os.path.join(user_dir, 'PingiVPN.png')

        if os.path.exists(config_file_path) and os.path.exists(qr_code_path):
            # Если файлы уже существуют, выходим из функции
            return

        # Копируем файлы из base_configs в папку пользователя
        free_files = sorted([f for f in os.listdir(BASE_CONFIGS_DIR) if f.endswith('_free.conf')])
        free_images = sorted([f for f in os.listdir(BASE_CONFIGS_DIR) if f.endswith('_free.png')])

        if free_files and free_images:
            # Копирование и переименование файлов
            shutil.copy(os.path.join(BASE_CONFIGS_DIR, free_files[0]), config_file_path)
            shutil.copy(os.path.join(BASE_CONFIGS_DIR, free_images[0]), qr_code_path)

            # Переименовываем использованные файлы
            os.rename(os.path.join(BASE_CONFIGS_DIR, free_files[0]),
                      os.path.join(BASE_CONFIGS_DIR, f"{free_files[0].split('_')[0]}_{chat_id}_Used.conf"))
            os.rename(os.path.join(BASE_CONFIGS_DIR, free_images[0]),
                      os.path.join(BASE_CONFIGS_DIR, f"{free_images[0].split('_')[0]}_{chat_id}_Used.png"))
        else:
            raise Exception("Нет доступных файлов для создания конфигурации")

    except Exception as e:
        print(f"Ошибка при создании файлов для пользователя {chat_id}: {e}")