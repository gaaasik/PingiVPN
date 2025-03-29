import os

from bot.handlers.cleanup import REGISTERED_USERS_DIR


#=============#
def find_user_directory(chat_id):
    """
    Поиск папки, которая содержит chat_id в своем имени.
    Возвращает путь к папке или None, если папка не найдена.
    """
    all_dirs = os.listdir(REGISTERED_USERS_DIR)  # REGISTERED_USERS_DIR должен быть объявлен в этом файле или импортирован

    # Ищем первую папку, в названии которой содержится chat_id
    for dir_name in all_dirs:
        if str(chat_id) in dir_name:
            return os.path.join(REGISTERED_USERS_DIR, dir_name)

    # Если не найдено, возвращаем None
    return None
#=============#





# import asyncio
# import os
# import shutil
# from aiogram.types import FSInputFile
# from dotenv import load_dotenv
# from bot.handlers.cleanup import store_important_message
#
# from bot.keyboards.reply import reply_keyboard
# from data.text_messages import  instructions_message
# # Загрузка переменных из файла .env
# load_dotenv()
# # Получение переменных окружения
# CONFIGS_DIR = os.getenv('CONFIGS_DIR')
# if CONFIGS_DIR is None:
#     raise ValueError("Переменная окружения CONFIGS_DIR не установлена.")
#
# BASE_CONFIGS_DIR = os.path.join(CONFIGS_DIR, 'base_configs')
# PATH_TO_IMAGES = os.getenv('PATH_TO_IMAGES')
# if PATH_TO_IMAGES is None:
#     raise ValueError("Переменная окружения PATH_TO_IMAGES не установлена.")
#
# REGISTERED_USERS_DIR = os.path.join(CONFIGS_DIR, 'registered_user')
#
# # Новая директория для зарегистрированных пользователей
#
# def check_existing_user_files(chat_id):
#     """
#     Проверяет, существует ли директория пользователя и содержатся ли в ней файлы конфигурации и изображения,
#     соответствующие chat_id.
#     """
#     # Папка пользователя определяется по chat_id
#     user_dir = os.path.join(REGISTERED_USERS_DIR, str(chat_id))
#     if os.path.exists(user_dir):
#         # Проверяем наличие файлов в этой директории
#         config_file = os.path.join(user_dir, "PingiVPN.conf")
#         qr_file = os.path.join(user_dir, "PingiVPN.png")
#         if os.path.exists(config_file) and os.path.exists(qr_file):
#             return True
#     return False
#
# async def send_files_to_user(message, chat_id, use_existing=False):
#     """
#     Отправка файлов пользователю через Telegram.
#     """
#     # Проверяем, существует ли уже папка и файлы пользователя
#     if check_existing_user_files(chat_id):
#         user_dir = os.path.join(REGISTERED_USERS_DIR, str(chat_id))
#         config_file_path = os.path.join(user_dir, 'PingiVPN.conf')
#         qr_code_path = os.path.join(user_dir, 'PingiVPN.png')
#
#         config_file = FSInputFile(config_file_path)
#         qr_code_file = FSInputFile(qr_code_path)
#     else:
#         # Логика для копирования свободных файлов и переименования
#         free_files = sorted([f for f in os.listdir(BASE_CONFIGS_DIR) if f.endswith('_free.conf')])
#         free_images = sorted([f for f in os.listdir(BASE_CONFIGS_DIR) if f.endswith('_free.png')])
#
#
#
#
#         if not free_files or not free_images:
#             # Используем резервные файлы general_adress
#             config_file_path = os.path.join(BASE_CONFIGS_DIR, 'general_adress.conf')
#             qr_code_path = os.path.join(BASE_CONFIGS_DIR, 'general_adress.png')
#         else:
#             # Копирование первых свободных файлов
#             user_dir = os.path.join(REGISTERED_USERS_DIR, str(chat_id))
#             if not os.path.exists(user_dir):
#                 os.makedirs(user_dir)
#             config_file_path = os.path.join(user_dir, 'PingiVPN.conf')
#             qr_code_path = os.path.join(user_dir, 'PingiVPN.png')
#
#             shutil.copy(os.path.join(BASE_CONFIGS_DIR, free_files[0]), config_file_path)
#             shutil.copy(os.path.join(BASE_CONFIGS_DIR, free_images[0]), qr_code_path)
#             # Переименование использованных файлов
#             os.rename(os.path.join(BASE_CONFIGS_DIR, free_files[0]),
#                       os.path.join(BASE_CONFIGS_DIR, f"{free_files[0].split('_')[0]}_{chat_id}_Used.conf"))
#             os.rename(os.path.join(BASE_CONFIGS_DIR, free_images[0]),
#                       os.path.join(BASE_CONFIGS_DIR, f"{free_images[0].split('_')[0]}_{chat_id}_Used.png"))
#
#         config_file = FSInputFile(config_file_path)
#         qr_code_file = FSInputFile(qr_code_path)
#
#     # Отправка файлов
#     await message.answer_document(document=config_file)
#     await message.answer_photo(photo=qr_code_file)
#
#     # Дополнительно: Отправка инструкции и изображения пингвина
#     penguin_image_path = os.path.join('images', 'Hello.png')
#     if os.path.exists(penguin_image_path):
#         penguin_image = FSInputFile(penguin_image_path)
#         await message.answer_photo(photo=penguin_image)
#
#     await message.answer(instructions_message,
#                          reply_markup=inline_kb,
#                          parse_mode='Markdown',
#                          disable_web_page_preview=True
#                          )
#
#     await store_important_message(message.chat.id, message.message_id, message)
# async def process_user_files(folder_name):
#     """
#     Обработка файлов пользователя: поиск свободных конфигурационных файлов и изображений,
#     перемещение их в директорию пользователя, переименование и отправка пользователю.
#     """
#     user_dir = os.path.join(REGISTERED_USERS_DIR, folder_name)  # Используем REGISTERED_USERS_DIR
#
#     # Проверка существования директории пользователя
#     if not os.path.exists(user_dir):
#         os.makedirs(user_dir)
#
#     # Проверяем, существует ли уже необходимый файл в папке пользователя
#     config_file_path = os.path.join(user_dir, 'PingiVPN.conf')
#     qr_file_path = os.path.join(user_dir, 'PingiVPN.png')
#
#     if os.path.exists(config_file_path) and os.path.exists(qr_file_path):
#         # Если файлы уже существуют, просто возвращаем их
#         config_file = FSInputFile(config_file_path)
#         qr_code_file = FSInputFile(qr_file_path)
#         return config_file, qr_code_file
#
#     # Поиск свободных файлов в директории BASE_CONFIGS_DIR
#     free_files = sorted([f for f in os.listdir(BASE_CONFIGS_DIR) if f.endswith('_free.conf')])
#     free_images = sorted([f for f in os.listdir(BASE_CONFIGS_DIR) if f.endswith('_free.png')])
#
#     paired_files = []
#     for conf_file in free_files:
#         base_name = conf_file.replace('_free.conf', '')
#         matching_image = f"{base_name}_free.png"
#         if matching_image in free_images:
#             paired_files.append((conf_file, matching_image))
#
#     if not paired_files:
#         # Проверка наличия general_adress.conf и general_adress.png
#         general_config = os.path.join(BASE_CONFIGS_DIR, 'general_adress.conf')
#         general_image = os.path.join(BASE_CONFIGS_DIR, 'general_adress.png')
#
#         if os.path.exists(general_config) and os.path.exists(general_image):
#             # Копирование general_adress файлов в директорию пользователя
#             shutil.copy(general_config, os.path.join(user_dir, 'PingiVPN.conf'))
#             shutil.copy(general_image, os.path.join(user_dir, 'PingiVPN.png'))
#
#             config_file = FSInputFile(os.path.join(user_dir, 'PingiVPN.conf'))
#             qr_code_file = FSInputFile(os.path.join(user_dir, 'PingiVPN.png'))
#             return config_file, qr_code_file
#         else:
#             raise Exception("Нет доступных пар конфигурационных файлов и изображений, и отсутствуют general_adress файлы.")
#
#     # Берем первую доступную пару
#     free_config_file, free_image_file = paired_files[0]
#
#     # Извлечение первого числа из имени файла
#     prefix_number = free_config_file.split('_')[0]
#
#     # Определение путей к новым файлам в директории пользователя
#     new_config_name = "PingiVPN.conf"
#     new_image_name = "PingiVPN.png"
#     new_config_path = os.path.join(user_dir, new_config_name)
#     new_image_path = os.path.join(user_dir, new_image_name)
#
#     # Копирование свободных файлов в директорию пользователя
#     shutil.copy(os.path.join(BASE_CONFIGS_DIR, free_config_file), new_config_path)
#     shutil.copy(os.path.join(BASE_CONFIGS_DIR, free_image_file), new_image_path)
#
#     # Переименование использованных файлов в директории BASE_CONFIGS_DIR с сохранением первого числа
#     used_config_name = f"{prefix_number}_{folder_name}_Used.conf"
#     used_image_name = f"{prefix_number}_{folder_name}_Used.png"
#     os.rename(os.path.join(BASE_CONFIGS_DIR, free_config_file), os.path.join(BASE_CONFIGS_DIR, used_config_name))
#     os.rename(os.path.join(BASE_CONFIGS_DIR, free_image_file), os.path.join(BASE_CONFIGS_DIR, used_image_name))
#
#     # Подготовка файлов для отправки через Telegram
#     config_file = FSInputFile(new_config_path)
#     qr_code_file = FSInputFile(new_image_path)
#
#     return config_file, qr_code_file
#
# # Цикл, который запускает process_user_files для чисел от 1 до 50
# async def run_process_for_numbers():
#     for i in range(1, 51):
#         phone_number = str(i)  # Используем номер от 1 до 50 в качестве имени файла или идентификатора
#         try:
#             await process_user_files(phone_number)
#             print(f"Процесс завершен успешно для номера {phone_number}")
#         except Exception as e:
#             print(f"Ошибка для номера {phone_number}: {str(e)}")
# # # Проверка, чтобы убедиться, что скрипт выполняется как основной
# # if __name__ == "__main__":
# #     # Запуск асинхронной функции через asyncio.run()
# #     asyncio.run(run_process_for_numbers())
# #
#
#
#
