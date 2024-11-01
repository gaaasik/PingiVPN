# bot/handlers/start.py
import os
from aiogram import Router, types
from aiogram.filters import Command
from dotenv import load_dotenv

from bot.handlers.admin import send_admin_log
from bot.handlers.all_menu.menu_connect_vpn import connect_text_messages, device_choice_keyboard
from bot.handlers.cleanup import register_message_type
from bot.utils.cache import send_cached_photo
from models.UserCl import UserCl

router = Router()
# Загрузка переменных из файла .env
load_dotenv()
PATH_TO_IMAGES = os.getenv('PATH_TO_IMAGES')  # Получаем путь к папке с изображениями

# Получение пути к папке с зарегистрированными пользователями
REGISTERED_USERS_DIR = os.getenv('REGISTERED_USERS_DIR')
referral_old_chat_id =0

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    chat_id = message.chat.id
    user = await message.bot.get_chat(chat_id)
    user_name_full = f"{user.first_name} {user.last_name or ''}".strip()
    user_login = message.from_user.username or None  # Используем None, если username отсутствует
    # Выводим значения с подписями
    # добавление реферального id
    args = message.text.split()[1] if len(message.text.split()) > 1 else None
    referral_old_chat_id = int(args) if args else None







    user = await UserCl.load_user(chat_id)

    if not user:
        # Если пользователя нет, добавляем его в базу данных
        print("Новый пользователь______________________Нужно админу")



        us = await UserCl.add_user_to_database(chat_id, user_name_full, user_login, referral_old_chat_id)

        print("УВЕДОМЛЕНИЕ АДМИНУ НЕЕЕТУ")
    else:
        await user.user_name_full.set(user_name_full)



    # Получаем ID чата и никнейм пользователя


    # Ищем директорию, которая содержит chat_id в названии
    matching_dirs = [d for d in os.listdir(REGISTERED_USERS_DIR) if str(chat_id) in d]

    if matching_dirs:
        # Если такая директория найдена, используем её
        user_dir = os.path.join(REGISTERED_USERS_DIR, matching_dirs[0])
    else:
        # Если директория не найдена, создаем новую
        # Если username пустой или None, используем только chat_id
        if not user_login:
            folder_name = f"{chat_id}"
        else:
            folder_name = f"{chat_id}_{user_login}"

        user_dir = os.path.join(REGISTERED_USERS_DIR, folder_name)
        os.makedirs(user_dir)
        print(f"Создана папка для пользователя {chat_id} с именем {user_login or chat_id}")

    # Приветственное сообщение с инлайн-кнопками для выбора устройства
    welcome_text = connect_text_messages

    # Формируем путь к картинке "hello.png"
    image_path = os.path.join(PATH_TO_IMAGES, "hello.png")

    # Отправка закешированного фото
    await send_cached_photo(message)
    sent_message = await message.answer("Приветствуем в мире надежного и скоростного VPN! 🚀\n\n", parse_mode="Markdown")
    sent_message = await message.answer(welcome_text, reply_markup=device_choice_keyboard(), parse_mode="Markdown")

    #await store_important_message(message.bot, message.chat.id, sent_message.message_id, sent_message,"start")
    await register_message_type(message.chat.id, sent_message.message_id, "start", message.bot)
    await send_admin_log(            bot=message.bot,
            message=f"Добавлен новый пользователь: (ID чата: {chat_id}) реферальный аргумент {referral_old_chat_id} \n"
        )
    # Получаем данные пользователя из базы данных


        # Получаем количество пользователей для уведомления администратора
        #count_users = await get_user_count()
        # Уведомляем администратора о новом пользователе
        # await send_admin_log(
        #     bot=message.bot,
        #     message=f"Добавлен новый пользователь: @{username} (ID чата: {chat_id}) \nКоличество пользователей: {count_users}"
        # )
