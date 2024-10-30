# bot/handlers/start.py
import os

from aiogram import Router, types
from aiogram.filters import Command
from dotenv import load_dotenv

from bot.handlers.cleanup import store_message, register_message_type
from bot.keyboards.inline import device_choice_keyboard
from bot.keyboards.reply import reply_keyboard_main_menu
from bot.utils.cache import send_cached_photo
from bot.all_message.text_messages import connect_text_messages
from models.UserCl import UserCl

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
    welcome_text = connect_text_messages

    # Формируем путь к картинке "hello.png"
    image_path = os.path.join(PATH_TO_IMAGES, "hello.png")

    # Сохраняем сообщение пользователя
    await store_message(message.chat.id, message.message_id, message.text, 'user')

    # Отправка закешированного фото
    await send_cached_photo(message)
    sent_message = await message.answer("Приветствуем в мире надежного и скоростного VPN! 🚀\n\n", parse_mode="Markdown")
    sent_message = await message.answer(welcome_text, reply_markup=device_choice_keyboard(),parse_mode="Markdown")
    #await store_important_message(message.bot, message.chat.id, sent_message.message_id, sent_message,"start")
    await register_message_type(message.chat.id, sent_message.message_id, "start", message.bot)

    # Уведомляем администратора о новом пользователе
    #count_users = await get_user_count()

    # Получаем данные пользователя из базы данных
    user = await UserCl.load_user(chat_id)


    if user:
        # Если пользователь уже существует, уведомляем администратора
        # await send_admin_log(
        #     bot=message.bot,
        #     message=f"Пользователь уже существует: @{username} (ID чата: {chat_id})"
        # )
        print("Пользователь уже есть______________________Нужно админу")
    else:
        # Если пользователя нет, добавляем его в базу данных
        print("Новый пользователь______________________Нужно админу")
        #await add_user_db(chat_id=chat_id, user_name=username)

        args = message.text.split()[1] if len(message.text.split()) > 1 else None
        print(f"args: {args}_________________________________________")
        referral_old_chat_id = int(args) if args else None
        print(f"referral: {referral_old_chat_id}_________________________________________")
        us = await UserCl.add_user_to_database(chat_id, username, referral_old_chat_id)

        print("УВЕДОМЛЕНИЕ АДМИНУ НЕЕЕТУ")

        # Получаем количество пользователей для уведомления администратора
        #count_users = await get_user_count()


        # Уведомляем администратора о новом пользователе
        # await send_admin_log(
        #     bot=message.bot,
        #     message=f"Добавлен новый пользователь: @{username} (ID чата: {chat_id}) \nКоличество пользователей: {count_users}"
        # )

    # Сохраняем в базе данных реферальную информацию (если есть)
    # args = message.text.split()[1] if len(message.text.split()) > 1 else None
    # if args:
    #     referral_old_chat_id = int(args)
    #     await add_referral(referral_old_chat_id, chat_id)

