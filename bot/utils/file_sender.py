# Это файл file_sender.py

import os
import shutil
from aiogram.types import FSInputFile
import logging

from bot.handlers.admin import send_admin_log
from bot.handlers.cleanup import store_important_message
from bot.utils.file_manager import find_user_directory
from data.text_messages import android_instructions, iphone_instructions, mac_instructions, linux_instructions, \
    windows_instructions
from dotenv import load_dotenv
from bot.utils.cache import cached_video  # Предполагаем, что видео кешируется аналогично фото
from main import PATH_TO_IMAGES

# Загрузка переменных окружения из .env
load_dotenv()
CONFIGS_DIR = os.getenv('CONFIGS_DIR')
BASE_CONFIGS_DIR = os.path.join(CONFIGS_DIR, 'base_configs')
REGISTERED_USERS_DIR = os.path.join(CONFIGS_DIR, 'registered_user')
USED_CONFIGS_DIR = os.path.join(CONFIGS_DIR, 'used_config')  # Директория для архивирования использованных файлов
# Пути к резервным файлам
GENERAL_CONFIG_FILE = os.path.join(BASE_CONFIGS_DIR, "general_adress.conf")
GENERAL_IMAGE_FILE = os.path.join(BASE_CONFIGS_DIR, "general_adress.png")


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
    username = callback_query.from_user.username or None

    print(f"Отправка конфигурационного файла для пользователя с chat_id: {chat_id}, username: {username or 'unknown'}")

    # Ищем папку пользователя, которая содержит chat_id в своем имени
    user_dir = find_user_directory(chat_id)  #=============#

    if not user_dir:  #=============#
        # Если папка не найдена, создаем новую
        folder_name = f"{chat_id}_{username}" if username else f"{chat_id}"
        user_dir = os.path.join(REGISTERED_USERS_DIR, folder_name)
        os.makedirs(user_dir)
        print(f"Создана новая папка: {user_dir}")

    # Пути к файлам
    config_file_path = os.path.join(user_dir, "PingiVPN.conf")
    qr_code_path = os.path.join(user_dir, "PingiVPN.png")

    # Проверяем, существуют ли оба файла в директории, если нет, вызываем create_user_files
    if not (os.path.exists(config_file_path) and os.path.exists(qr_code_path)):
        print(f"Не все файлы существуют. Вызываем create_user_files.")
        await create_user_files(chat_id, username, callback_query.bot)

    # Проверяем наличие конфигурационного файла после создания и отправляем его, если он существует
    if os.path.exists(config_file_path):
        print(f"Файл {config_file_path} найден. Отправляем файл пользователю.")
        await callback_query.message.answer_document(FSInputFile(config_file_path))
    else:
        print(f"Файл {config_file_path} не найден даже после создания.")
        await callback_query.message.answer("Конфигурационный файл не найден.")


# Отправка видео пользователю
async def send_instruction_video(callback_query):
    """
    Отправка видео с инструкцией пользователю через Telegram.
    """
    # Проверяем, закешировано ли видео
    if cached_video:
        # Отправляем видео пользователю
        message = await callback_query.message.answer_video(cached_video)
        return message
    else:
        # Если видео не закешировано, проверяем наличие файла и отправляем
        video_path = os.path.join(PATH_TO_IMAGES, "instructions_iPhone.mp4")
        if os.path.exists(video_path):

            message = await callback_query.message.answer_video(FSInputFile(video_path))
            return message
        else:
            # Если видеофайл не найден, возвращаем сообщение об ошибке
            print("Не смогли отправить видео")
            return


async def send_qr_code(callback_query):
    """
    Отправка QR-кода пользователю через Telegram.
    """
    chat_id = callback_query.message.chat.id
    username = callback_query.from_user.username or None

    print(f"Отправка QR-кода для пользователя с chat_id: {chat_id}, username: {username or 'unknown'}")

    # Ищем папку пользователя, которая содержит chat_id в своем имени
    user_dir = find_user_directory(chat_id)  #=============#

    if not user_dir:  #=============#
        # Если папка не найдена, создаем новую
        folder_name = f"{chat_id}_{username}" if username else f"{chat_id}"
        user_dir = os.path.join(REGISTERED_USERS_DIR, folder_name)
        os.makedirs(user_dir)
        print(f"Создана новая папка: {user_dir}")

    # Пути к файлам
    config_file_path = os.path.join(user_dir, "PingiVPN.conf")
    qr_code_path = os.path.join(user_dir, "PingiVPN.png")

    # Проверяем, существуют ли оба файла в директории, если нет, вызываем create_user_files
    if not (os.path.exists(config_file_path) and os.path.exists(qr_code_path)):
        print(f"Не все файлы существуют. Вызываем create_user_files.")
        await create_user_files(chat_id, username, callback_query.bot)

    # Проверяем наличие QR-кода после создания и отправляем его, если он существует
    if os.path.exists(qr_code_path):
        print(f"Файл {qr_code_path} найден. Отправляем QR-код пользователю.")
        await callback_query.message.answer_photo(FSInputFile(qr_code_path))
    else:
        print(f"Файл {qr_code_path} не найден даже после создания.")
        await callback_query.message.answer("QR-код не найден.")


async def create_user_files(chat_id, username, bot):
    try:
        # Ищем папку пользователя, которая содержит chat_id в своем имени
        user_dir = find_user_directory(chat_id)  #=============#

        if not user_dir:  #=============#
            # Если папка не найдена, создаем новую
            folder_name = f"{chat_id}_{username}" if username else f"{chat_id}"
            user_dir = os.path.join(REGISTERED_USERS_DIR, folder_name)
            os.makedirs(user_dir)
            print(f"Создана новая папка: {user_dir}")

        # Проверяем, существуют ли уже необходимые файлы
        config_file_path = os.path.join(user_dir, 'PingiVPN.conf')
        qr_code_path = os.path.join(user_dir, 'PingiVPN.png')

        # Если файлы уже существуют, не создаем новые
        if os.path.exists(config_file_path) and os.path.exists(qr_code_path):
            print(f"Файлы уже существуют для пользователя {chat_id}. Новые файлы не создаются.")
            return  # Файлы уже существуют, не нужно создавать новые

        # Копируем файлы из base_configs в папку пользователя
        free_files = sorted([f for f in os.listdir(BASE_CONFIGS_DIR) if f.endswith('_free.conf')])
        free_images = sorted([f for f in os.listdir(BASE_CONFIGS_DIR) if f.endswith('_free.png')])

        if free_files and free_images:
            # Копирование и переименование файлов для пользователя
            shutil.copy(os.path.join(BASE_CONFIGS_DIR, free_files[0]), config_file_path)
            shutil.copy(os.path.join(BASE_CONFIGS_DIR, free_images[0]), qr_code_path)

            # Переименование и перемещение использованных файлов в архив
            archive_used_files(chat_id, username, free_files[0], free_images[0])

            conf_files_count, png_files_count = count_files_in_directory()
            await send_admin_log(bot, f" Созданы файлы для {chat_id} {username}. осталось {conf_files_count} файлов и \n"
                                      f"{png_files_count} картинок")
        else:
            # Если нет доступных файлов, используем резервные файлы
            if os.path.exists(GENERAL_CONFIG_FILE) and os.path.exists(GENERAL_IMAGE_FILE):
                # Копируем резервные файлы в папку пользователя
                shutil.copy(GENERAL_CONFIG_FILE, config_file_path)
                shutil.copy(GENERAL_IMAGE_FILE, qr_code_path)

                print(f"Пользователю {chat_id} отправлены общие конфигурационные файлы.")

                # Уведомление администратору о том, что закончились конфигурационные файлы
                admin_chat_id = 456717505  # ID чата администратора
                warning_message = (
                    f"⚠️ Warning!!! Закончились конфигурационные файлы для пользователей.\n"
                    f"Пользователю {chat_id} были отправлены общие конфигурационные файлы."
                )
                await bot.send_message(admin_chat_id, warning_message)
            else:
                raise Exception("Резервные конфигурационные файлы также не найдены!")

    except Exception as e:
        error_message = f"Ошибка при создании файлов для пользователя {chat_id}: {e}"
        logging.error(error_message)


def remove_old_files(user_dir):
    """Удаляет старые конфигурационные файлы пользователя"""
    try:
        old_config = os.path.join(user_dir, 'PingiVPN.conf')
        old_qr = os.path.join(user_dir, 'PingiVPN.png')

        if os.path.exists(old_config):
            os.remove(old_config)

        if os.path.exists(old_qr):
            os.remove(old_qr)

    except Exception as e:
        logging.error(f"Ошибка при удалении старых файлов для пользователя: {e}")


def archive_used_files(chat_id, username, config_file, image_file):
    """Переименовывает и архивирует использованные файлы"""
    try:
        # Извлекаем номер файла из его имени (например, 58 из 58_free.conf)
        file_number = config_file.split('_')[0]

        # Формируем новые имена для архивированных файлов, сохраняя номер файла
        new_config_name = f"{file_number}_{chat_id}_{username}_Used.conf"
        new_image_name = f"{file_number}_{chat_id}_{username}_Used.png"

        # Перемещаем файлы из base_configs в used_config
        shutil.move(os.path.join(BASE_CONFIGS_DIR, config_file),
                    os.path.join(USED_CONFIGS_DIR, new_config_name))
        shutil.move(os.path.join(BASE_CONFIGS_DIR, image_file),
                    os.path.join(USED_CONFIGS_DIR, new_image_name))

        logging.info(
            f"Файлы {config_file} и {image_file} успешно перемещены и переименованы для пользователя {chat_id}")

    except Exception as e:
        logging.error(f"Ошибка при архивировании файлов для пользователя {chat_id}: {e}")


# Функция для подсчета файлов с указанными шаблонами (*_free.conf и *_free.png)
def count_files_in_directory():
    """
    Считает количество файлов, оканчивающихся на _free.conf и _free.png в указанной директории.
    Возвращает количество конфигурационных файлов и количество изображений.
    Обрабатывает возможные ошибки, такие как отсутствие доступа к директории или ее несуществование.
    """
    try:
        # Приводим путь к стандартному виду для ОС (в Windows заменяет обратные слеши)

        directory = os.path.normpath(BASE_CONFIGS_DIR)

        # Проверяем, существует ли директория
        if not os.path.exists(directory):
            raise FileNotFoundError(f"Директория {directory} не найдена.")

        # Проверяем, является ли путь директорией
        if not os.path.isdir(directory):
            raise NotADirectoryError(f"{directory} не является директорией.")

        # Выводим содержимое директории для проверки
        files_in_directory = os.listdir(directory)
        print(f"Содержимое директории {directory}: {files_in_directory}")

        # Считаем файлы с нужными расширениями
        conf_files = len([f for f in files_in_directory if f.endswith('_free.conf')])
        png_files = len([f for f in files_in_directory if f.endswith('_free.png')])

        return conf_files, png_files

    except FileNotFoundError as e:
        logging.error(f"Ошибка: {e}")
        return 0, 0  # Возвращаем 0, если директория не найдена

    except NotADirectoryError as e:
        logging.error(f"Ошибка: {e}")
        return 0, 0  # Возвращаем 0, если путь не является директорией

    except PermissionError as e:
        logging.error(f"Ошибка доступа к директории {directory}: {e}")
        return 0, 0  # Возвращаем 0 в случае проблем с доступом

    except Exception as e:
        logging.error(f"Непредвиденная ошибка при подсчете файлов в директории {directory}: {e}")
        return 0, 0  # Возвращаем 0 в случае любой другой ошибки
