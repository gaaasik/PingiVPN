# bot/handlers/start.py
import os

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from dotenv import load_dotenv

from bot.handlers.cleanup import store_message, store_important_message
from bot.keyboards.inline import device_choice_keyboard
from bot.keyboards.reply import reply_keyboard
from bot.utils.db import add_user, drop_table, get_user_by_telegram_id, add_referral, get_user_count
from bot.utils.file_manager import send_files_to_user


router = Router()
# Загрузка переменных из файла .env
load_dotenv()
PATH_TO_IMAGES = os.getenv('PATH_TO_IMAGES')  # Получаем путь к папке с изображениями
# Получение пути к папке с зарегистрированными пользователями
REGISTERED_USERS_DIR = os.getenv('REGISTERED_USERS_DIR')


@router.message(Command("start"))
async def cmd_start(message: types.Message):


    # Получаем ID чата и никнейм пользователя
    chat_id = message.chat.id
    username = message.from_user.username or str(message.from_user.id) or "unknown"
    folder_name = f"{chat_id}_{username}"  # Формируем название папки как id_имя пользователя
    user_dir = os.path.join(REGISTERED_USERS_DIR, folder_name)

    # Создание папки пользователя, если её нет
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
        print(f"Создана папка для пользователя {chat_id} с именем {username}")
    # Приветственное сообщение с инлайн-кнопками для выбора устройства
    welcome_text = "На каком устройстве вы хотите настроить VPN?"

    # Формируем путь к картинке "hello.png"
    image_path = os.path.join(PATH_TO_IMAGES, "hello.png")
    # Сохраняем сообщение пользователя
    await store_message(message.chat.id, message.message_id, message.text, 'user')
    # Проверяем, существует ли изображение по указанному пути
    if os.path.exists(image_path):
        # Отправляем изображение пользователю, передаем путь напрямую
        await message.answer_photo(photo=FSInputFile(image_path))
    else:
        # Если файл не найден, отправляем сообщение об ошибке
        print("Изображение hello.png не найдено, проверьте путь к файлу.")


    sent_message = await message.answer(welcome_text, reply_markup=device_choice_keyboard())
    await store_important_message(message.chat.id, sent_message.message_id, sent_message)

    # Проверяем, если пользователь существует в базе данных
    user = await get_user_by_telegram_id(message.from_user.id)

    if not user:
        # Регистрируем нового пользователя
        await add_user(
            chat_id=chat_id,
            user_name=username,
        )
        # Уведомляем администратора о новом пользователе
        count_users = await get_user_count()
        await message.bot.send_message(
            chat_id=456717505,  # ID админа для уведомления
            text=f"Добавлен новый пользователь: @{username} (ID чата: {chat_id}) \n Количество пользователей: {count_users}"
        )

    # Сохраняем в базе данных реферальную информацию (если есть)
    args = message.text.split()[1] if len(message.text.split()) > 1 else None
    if args:
        referrer_id = int(args)
        await add_referral(referrer_id, chat_id)




#старый код
# @router.message(Command("start"))
# async def cmd_start(message: types.Message):
#
#     # Проверяем, есть ли аргументы в команде /start
#     if len(message.text.split()) > 1:
#         args = message.text.split()[1]  # Аргумент передается после команды /start
#     else:
#         args = None  # Если аргументов нет
#     # Сохраняем сообщение в базе данных
#     await store_message(message.chat.id, message.message_id, message.text, 'user')
#
#     # Получаем ID чата и никнейм пользователя
#     chat_id = message.chat.id
#     username = message.from_user.username or "unknown"
#     # Отправляем приветственное сообщение
#     sent_message = await message.answer(welcome_message, reply_markup=reply_keyboard)
#     await store_important_message(message.chat.id, sent_message.message_id, sent_message)
#
#     # Формируем название папки как "id чата_никнейм пользователя"
#     folder_name = f"{chat_id}_{username}"
#
#     # Проверяем, если пользователь существует в базе данных
#     user = await get_user_by_telegram_id(message.from_user.id)
#     # Если это новый пользователь, регистрируем его
#     referrer_id = int(args) if args else None  # Если есть реферальный код, используем его
#
#     # Проверяем, зарегистрирован ли пользователь
#     if not user:
#            # Если это новый пользователь, регистрируем его
#             await add_user(
#                 chat_id=message.from_user.id,
#                 user_name=message.from_user.username or message.from_user.first_name,
#                 referrer_id=referrer_id  # Сохраняем ID пригласившего пользователя
#             )
#             # Отправляем уведомление в чат 456717505
#             await message.bot.send_message(
#                 chat_id=456717505,  # ID чата для уведомления
#                 text=f"Добавлен новый пользователь: {username} (ID чата: {chat_id})"
#             )
#
#     # Если есть пригласивший, сохраняем эту информацию
#     if referrer_id:
#         await add_referral(referrer_id, message.from_user.id)
#
#     # Отправка файлов пользователю
#     await send_files_to_user(message, folder_name, use_existing=False)
