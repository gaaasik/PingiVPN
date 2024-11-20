import logging
import os
from aiogram import Router, types
from aiogram.filters import Command
from dotenv import load_dotenv

from bot.database.referrals_db import process_referral_start
from bot.handlers.admin import send_admin_log
from bot.handlers.all_menu.menu_connect_vpn import connect_text_messages, device_choice_keyboard
from bot.handlers.cleanup import register_message_type
from bot.keyboards.reply import reply_keyboard_main_menu
from bot.utils.cache import send_cached_photo
from models.UserCl import UserCl

router = Router()

# Загрузка переменных из файла .env
load_dotenv()
PATH_TO_IMAGES = os.getenv('PATH_TO_IMAGES')
REGISTERED_USERS_DIR = os.getenv('REGISTERED_USERS_DIR')

# Проверка, что папка для пользователей установлена
if not REGISTERED_USERS_DIR:
    logging.error("Переменная среды REGISTERED_USERS_DIR не найдена.")

# Проверка существования пользователя
async def user_exists(chat_id: int) -> bool:
    try:
        user = await UserCl.load_user(chat_id)
        return user is not None
    except Exception as e:
        logging.error(f"Ошибка при проверке существования пользователя {chat_id}: {e}")
        return False

async def handle_referral(chat_id, referral_old_chat_id, bot):
    # Проверка существования пользователя перед обработкой реферала
    if await user_exists(chat_id):
        logging.info(f"Пользователь {chat_id} уже существует, повторная регистрация не требуется.")
        return

    # Получение данных о новом пользователе и отправка сообщения рефереру
    new_user = await bot.get_chat(chat_id)
    new_user_name = new_user.username or new_user.full_name
    referral_message = (
        f"🎉 Ура! Пользователь {new_user_name} (@{new_user.username or '—'}) присоединился к Pingi VPN по вашей ссылке."
        " При начале его использования сервиса вам будут начислены бонусные дни! 🎁"
    )

    try:
        await bot.send_message(referral_old_chat_id, referral_message)
        logging.info(f"Сообщение отправлено реферальному ID: {referral_old_chat_id}")
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения рефереру {referral_old_chat_id}: {e}")

    await process_referral_start(chat_id, referral_old_chat_id)

# Функция для обработки папок пользователей
def get_user_directory(chat_id, user_login):
    # Проверка существования корневой директории
    if not os.path.isdir(REGISTERED_USERS_DIR):
        logging.error("Корневая директория пользователей не найдена.")
        return None

    matching_dirs = [d for d in os.listdir(REGISTERED_USERS_DIR) if str(chat_id) in d]
    if matching_dirs:
        user_dir = os.path.join(REGISTERED_USERS_DIR, matching_dirs[0])
    else:
        folder_name = f"{chat_id}_{user_login}" if user_login else str(chat_id)
        user_dir = os.path.join(REGISTERED_USERS_DIR, folder_name)
        try:
            os.makedirs(user_dir, exist_ok=True)
            logging.info(f"Создана папка для пользователя {chat_id} с именем {user_login or chat_id}")
        except OSError as e:
            logging.error(f"Ошибка при создании папки для пользователя {chat_id}: {e}")
            return None
    return user_dir

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    bot = message.bot
    chat_id = message.chat.id
    user = await bot.get_chat(chat_id)
    user_name_full = f"{user.first_name} {user.last_name or ''}".strip()
    user_login = message.from_user.username or None
    args = message.text.split()[1] if len(message.text.split()) > 1 else None
    referral_old_chat_id = int(args) if args else None

    # Проверка и обработка реферального ID до загрузки пользователя
    if referral_old_chat_id:
        await handle_referral(chat_id, referral_old_chat_id, bot)

    # Проверяем, есть ли пользователь в базе данных, и добавляем, если его нет
    user = await UserCl.load_user(chat_id)
    if not user:
        logging.info("Регистрация нового пользователя.")
        await UserCl.add_user_to_database(chat_id, user_name_full, user_login, referral_old_chat_id)
        await send_admin_log(bot, f"Добавлен новый пользователь: ID чата: {chat_id} с рефералом {referral_old_chat_id}")
    else:
        await user.user_name_full.set(user_name_full)

    # Создание или получение пути пользователя
    user_dir = get_user_directory(chat_id, user_login)


    # Приветственное сообщение с изображением
    welcome_text = connect_text_messages
    await send_cached_photo(message)
    await message.answer(
        "🧊 Добро пожаловать 🚀\n\n"
        "🥶 Мы *кардинально* выделяемся, потому что используем уникальные серверы в *Антарктиде*\n\n"
        "🧊 И предлагаем *неограниченную* скорость и безопасность!",
        parse_mode="Markdown", reply_markup=reply_keyboard_main_menu
    )
    sent_message = await message.answer(welcome_text, reply_markup=device_choice_keyboard(), parse_mode="Markdown")

    await register_message_type(chat_id, sent_message.message_id, "start", bot)

