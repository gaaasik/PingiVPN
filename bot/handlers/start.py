import logging
import os

import aiosqlite
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery
from dotenv import load_dotenv

from bot.handlers.admin import send_admin_log, get_admin_reply_keyboard,ADMIN_CHAT_IDS
from bot.handlers.cleanup import register_message_type
from bot.keyboards.inline import accept_agreement_keyboard, device_choice_keyboard
from bot.keyboards.reply import reply_keyboard_main_menu
from bot.utils.cache import send_cached_photo
from models.UserCl import UserCl
from models.referral_class.ReferralCL import ReferralCl  # Импортируем новый класс ReferralCl
router = Router()

# Загрузка переменных из файла .env
load_dotenv()
PATH_TO_IMAGES = os.getenv('PATH_TO_IMAGES')
REGISTERED_USERS_DIR = os.getenv('REGISTERED_USERS_DIR')
connect_text_messages1 = (

    "🌐 Узнайте, что такое настоящее VPN подключение\n\n"
    "🚀 Ваша скорость ограничена только вашим провайдером!\n\n "

    "🔐 Гарантируем защиту ваших данных \n\n"

    "📱 *Выберите устройство для настройки VPN*"
)
# Проверка, что папка для пользователей установлена
if not REGISTERED_USERS_DIR:
    logging.error("Переменная среды REGISTERED_USERS_DIR не найдена.")


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

async def check_user_agreement(chat_id):
    """ Проверяет, принял ли пользователь соглашение. """
    async with aiosqlite.connect(os.getenv('database_path_local')) as db:
        async with db.execute("SELECT has_accepted_agreement FROM users WHERE chat_id = ?", (chat_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else False  # Если пользователя нет в базе, считаем, что соглашение не принято


async def request_user_agreement(bot, chat_id):
    """ Отправляет пользователю запрос на принятие соглашения. """
    welcome_text = (
        "🌐 Узнайте, что такое настоящее VPN подключение\n\n"
        "🚀 Ваша скорость ограничена только вашим провайдером!\n\n"
        "🔐 Гарантируем защиту ваших данных\n\n"
        "⚠️ *Чтобы начать, необходимо принять пользовательское соглашение.*\n\n"
        "📜 [Пользовательское соглашение](https://telegra.ph/Polzovatelskoe-soglashenie-03-07-7)"
    )

    await bot.send_message(
        chat_id,
        welcome_text,
        reply_markup=accept_agreement_keyboard(),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    bot = message.bot
    chat_id = message.chat.id
    user = await bot.get_chat(chat_id)
    user_name_full = f"{user.first_name} {user.last_name or ''}".strip()
    user_login = message.from_user.username or None
    args = message.text.split()[1] if len(message.text.split()) > 1 else None
    referral_old_chat_id = int(args) if args else None

    # Проверяем, есть ли пользователь в базе данных, и добавляем, если его нет
    user = await UserCl.load_user(chat_id)
    if not user:
        logging.info("Регистрация нового пользователя.")
        try:
            await UserCl.add_user_to_database(chat_id, user_name_full, user_login, referral_old_chat_id)
            # Создание или получение пути пользователя
            user_dir = get_user_directory(chat_id, user_login)
        except Exception as e:
            await send_admin_log(bot, f"Ошибка регистрации пользователя {chat_id}: {e}")

        # Если есть реферальный ID, обрабатываем через ReferralCl
        if referral_old_chat_id:
            try:
                await ReferralCl.handle_referral(chat_id, referral_old_chat_id, bot)
                await send_admin_log(bot,
                                     f"Добавлен новый пользователь @{user_login}: ID чата: {chat_id} с рефералом {referral_old_chat_id}")
            except Exception as e:
                logging.error(f"Ошибка при обработке реферала: {e}")
        else:
            await send_admin_log(bot,
                                 f"Добавлен новый пользователь @{user_login}: ID чата: {chat_id}")

    # Приветственное сообщение с изображением
    welcome_text = (
        "🌐 Узнайте, что такое настоящее VPN подключение\n\n"
        "🚀 Ваша скорость ограничена только вашим провайдером!\n\n"
        "🔐 Гарантируем защиту ваших данных\n\n"
        "⚠️ *Чтобы начать, необходимо принять пользовательское соглашение.*\n\n"
        "📜 [Пользовательское соглашение](https://telegra.ph/Polzovatelskoe-soglashenie-03-07-7)"
    )

    await send_cached_photo(message)
    reply_markup = get_admin_reply_keyboard() if chat_id in ADMIN_CHAT_IDS else reply_keyboard_main_menu

    await message.answer(
        "🧊 Добро пожаловать 🚀\n\n"
        "🥶 Мы *кардинально* выделяемся, потому что используем уникальные серверы в *Антарктиде*\n\n"
        "🧊 И предлагаем *неограниченную* скорость и безопасность!",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    # Проверяем, принял ли пользователь соглашение
    has_accepted = await check_user_agreement(chat_id)
    if not has_accepted:
        await request_user_agreement(bot, chat_id)
    else:
        sent_message = await message.answer(connect_text_messages1, reply_markup=device_choice_keyboard(),
                                                       parse_mode="Markdown")
    # Регистрируем сообщение типа "start"
    #await register_message_type(chat_id, sent_message.message_id, "start", bot)
@router.callback_query(F.data == "accept_agreement")
async def accept_agreement(callback: CallbackQuery):
    """Обработчик кнопки 'Принять соглашение'."""
    chat_id = callback.from_user.id

    # Обновляем статус принятия соглашения
    async with aiosqlite.connect(os.getenv('database_path_local')) as db:
        await db.execute("UPDATE users SET has_accepted_agreement = TRUE WHERE chat_id = ?", (chat_id,))
        await db.commit()

    await callback.message.edit_text("✅ Вы приняли пользовательское соглашение. Теперь выберите устройство для подключения.")
    sent_message = await callback.message.answer(connect_text_messages1, reply_markup=device_choice_keyboard(),
                                                       parse_mode="Markdown")
    await callback.answer()
