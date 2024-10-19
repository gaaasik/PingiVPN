# bot/handlers/start.py
import os

from aiogram import Router, types
from aiogram.filters import Command
from dotenv import load_dotenv

from bot.handlers.admin import send_admin_log
from bot.handlers.cleanup import store_message, store_important_message, register_message_type
from bot.keyboards.inline import device_choice_keyboard
from bot.utils.cache import send_cached_photo
from bot.database.db import get_user_by_telegram_id, add_referral, get_user_count
from bot.database.users_db import add_user_db

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
    username = message.from_user.username or None  # Используем None, если username отсутствует

    # Ищем директорию, которая содержит chat_id в названии
    matching_dirs = [d for d in os.listdir(REGISTERED_USERS_DIR) if str(chat_id) in d]

    if matching_dirs:
        # Если такая директория найдена, используем её
        user_dir = os.path.join(REGISTERED_USERS_DIR, matching_dirs[0])
    else:
        # Если директория не найдена, создаем новую
        # Если username пустой или None, используем только chat_id
        if not username:
            folder_name = f"{chat_id}"
        else:
            folder_name = f"{chat_id}_{username}"

        user_dir = os.path.join(REGISTERED_USERS_DIR, folder_name)
        os.makedirs(user_dir)
        print(f"Создана папка для пользователя {chat_id} с именем {username or chat_id}")

    # Приветственное сообщение с инлайн-кнопками для выбора устройства
    welcome_text = "На каком устройстве вы хотите настроить VPN?"

    # Формируем путь к картинке "hello.png"
    image_path = os.path.join(PATH_TO_IMAGES, "hello.png")

    # Сохраняем сообщение пользователя
    await store_message(message.chat.id, message.message_id, message.text, 'user')

    # Отправка закешированного фото
    await send_cached_photo(message)

    sent_message = await message.answer(welcome_text, reply_markup=device_choice_keyboard())
    await store_important_message(message.bot, message.chat.id, sent_message.message_id, sent_message,"start")
    await register_message_type(message.chat.id,sent_message.message_id,"start",message.bot)
    # Получаем данные пользователя из базы данных (включая устройство)
    user = await get_user_by_telegram_id(message.from_user.id)
    # Уведомляем администратора о новом пользователе
    count_users = await get_user_count()
    # Получаем данные пользователя из базы данных
    user = await get_user_by_telegram_id(chat_id)
    print(user)
    test = 111122222

    if user:
        # Если пользователь уже существует, уведомляем администратора
        await send_admin_log(
            bot=message.bot,
            message=f"Пользователь уже существует: @{username} (ID чата: {chat_id})"
        )
    else:
        # Если пользователя нет, добавляем его в базу данных
        await add_user_db(chat_id=chat_id, user_name=username)

        # Получаем количество пользователей для уведомления администратора
        count_users = await get_user_count()

        # Уведомляем администратора о новом пользователе
        await send_admin_log(
            bot=message.bot,
            message=f"Добавлен новый пользователь: @{username} (ID чата: {chat_id}) \nКоличество пользователей: {count_users}"
        )

    # Сохраняем в базе данных реферальную информацию (если есть)
    args = message.text.split()[1] if len(message.text.split()) > 1 else None
    if args:
        referrer_id = int(args)
        await add_referral(referrer_id, chat_id)

