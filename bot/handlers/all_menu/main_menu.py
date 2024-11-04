from aiogram import Router, types, Bot, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from bot.handlers.cleanup import delete_unimportant_messages, store_message, messages_for_db, register_message_type
import os

from flask_app.all_utils_flask_db import logger
from models.UserCl import UserCl
from bot.keyboards.inline import main_menu_inline_keyboard

router = Router()

from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# Функция для получения корректного склонения для дней
def get_days_text(days):
    if 11 <= days % 100 <= 14:
        return f"{days} дней"
    elif days % 10 == 1:
        return f"{days} день"
    elif 2 <= days % 10 <= 4:
        return f"{days} дня"
    else:
        return f"{days} дней"


# Функция для получения количества дней с момента регистрации
async def get_count_days_since_registration(us):
    try:
        # Предполагаем, что дата регистрации хранится в формате "дд.мм.гггг чч:мм:сс"
        registration_date_str = await us.registration_date.get()
        registration_date = datetime.strptime(registration_date_str, "%d.%m.%Y %H:%M:%S")
        days_since_registration = (datetime.now() - registration_date).days
        days_text = get_days_text(days_since_registration)

        # Формируем сообщение в зависимости от количества дней
        if days_since_registration == 0:
            return "🎉 Вы с нами Первый день! Настройте VPN один раз и забудьте о проблемах с доступом! 🚀"
        else:
            return f"🕓 Вы с нами уже {days_text}! Мы ценим ваше доверие! 🚀"
    except Exception as e:
        logger.error("Ошибка при расчёте дней с момента регистрации: %s", e)
        return "Произошла ошибка при проверке даты регистрации."


async def get_user_status_text(us):
    try:
        # Получаем количество ключей
        count_key = await us.count_key.get()

        if count_key == 0:
            # Если ключей нет
            return f"Нажмите *Подключить VPN*\n"

        # Проверяем статус первого ключа
        status_key = await us.servers[0].status_key.get()
        end_date_str = await us.servers[0].date_key_off.get_date()

        # Парсим строку даты в объект datetime для расчётов
        end_date = datetime.strptime(end_date_str, "%d.%m.%Y")

        # Рассчитываем оставшиеся дни
        today = datetime.now()
        remaining_days = (end_date - today).days

        # Формируем текст статуса в зависимости от статуса ключа
        if status_key == "free_key":
            return f"Пробный период до *{end_date_str}* (осталось {remaining_days} дней)"

        elif status_key == "blocked":
            return "*Ключ заблокирован*"

        elif status_key == "active":
            return f"Ключ активен до *{end_date_str}* (осталось {remaining_days} дней)"

        else:
            return "Статус ключа не распознан"

    except Exception as e:
        logger.error("Ошибка при проверке статуса пользователя: %s", e)
        return "Произошла ошибка при проверке статуса. Попробуйте позже."


# Функция для отображения основного меню
async def show_main_menu(chat_id: int, bot: Bot):
    user = await UserCl.load_user(chat_id)

    if not user:
        await bot.send_message(chat_id, "Для начала нажмите /start")
        return

    # Получаем данные о пользователе по chat_id
    us = await UserCl.load_user(chat_id)

    user_name_full = await us.user_name_full.get()
    days_since_registration_text = await get_count_days_since_registration(us)

    # Получаем статус пользователя
    status_text = await get_user_status_text(us)

    # Формирование текста главного меню
    text = (
        f"Привет {user_name_full}! 🕶\n\n"
        "PingiVPN - быстрый и безопасный доступ к свободному интернету без ограничений\n\n"
        "📱 Доступ к любым социальным сетям\n"
        "🛡 Анонимность\n"
        "📶 Устойчивость к блокировкам\n"
        "🚀 Высокая скорость\n"
        "💻 Поддержка любых устройств\n\n"
        f"🔑 Статус: {status_text}\n"
        f"{days_since_registration_text}\n"
    )

    # Отправка сообщения с меню
    await bot.send_message(chat_id=chat_id, text=text, reply_markup=main_menu_inline_keyboard(), parse_mode="Markdown")


# Обработчики для кнопок главного меню
@router.message(F.text == "🏠 Главное меню")
@router.message(Command(commands=["menu"]))
@router.callback_query(F.data == "main_menu")
async def handle_main_menu(event: types.Message | types.CallbackQuery):
    # Проверяем тип события (Message или CallbackQuery)
    if isinstance(event, types.CallbackQuery):
        chat_id = event.message.chat.id
        bot = event.bot
        await event.answer()  # Закрыть CallbackQuery, чтобы Telegram не показывал часы загрузки
    else:
        chat_id = event.chat.id
        bot = event.bot

    # Отображение главного меню
    await show_main_menu(chat_id, bot)
