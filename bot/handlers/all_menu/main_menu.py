import asyncio

from aiogram import Router, types, Bot, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from bot.handlers.cleanup import delete_unimportant_messages, store_message, messages_for_db, register_message_type
import os

#from fastapi_app.all_utils_flask_db import logger
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
    """
    Проверяет статус пользователя и возвращает текст статуса.
    """
    try:
        # Получаем количество ключей
        count_key = await us.count_key.get()
        logger.info(f"Количество ключей: {count_key}")

        if count_key == 0:
            # Если ключей нет
            logger.info("У пользователя нет ключей. Возвращаем сообщение о подключении VPN.")
            return f"Нажмите *Подключить VPN*\n"

        # Проверяем статус первого ключа
        status_key = await us.servers[0].status_key.get()
        logger.info(f"Статус первого ключа: {status_key}")

        end_date_str = await us.servers[0].date_key_off.get_date()
        logger.info(f"Дата окончания ключа: {end_date_str}")

        # Парсим строку даты в объект datetime для расчётов
        try:
            end_date = datetime.strptime(end_date_str, "%d.%m.%Y")
        except ValueError as date_error:
            logger.error(f"Ошибка преобразования строки даты {end_date_str} в объект datetime: {date_error}")
            return "Неверный формат даты ключа. Обратитесь в поддержку."

        # Рассчитываем оставшиеся дни
        today = datetime.now()
        remaining_days = (end_date - today).days
        logger.info(f"Сегодня: {today.strftime('%d.%m.%Y')}, осталось {remaining_days} дней до окончания ключа.")

        # Формируем текст статуса в зависимости от статуса ключа
        if status_key == "free_key":
            return f"Пробный период до *{end_date_str}* (осталось {remaining_days} дней)"

        elif status_key == "blocked":
            return "*Ключ заблокирован*"

        elif status_key == "active":
            expiration_text = ""
            if remaining_days > 2:
                expiration_text = f"Ключ активен до *{end_date_str}* (осталось {remaining_days} дней)"
            elif remaining_days >= 0 and remaining_days < 3:
                expiration_text = f"Ключ активен до *{end_date_str}* (осталось {remaining_days} дней)"
            elif remaining_days < 0:
                expiration_text = f"*Требуется оплата*"
            return expiration_text


        else:
            logger.warning(f"Неизвестный статус ключа: {status_key}")
            return "Статус ключа не распознан"

    except Exception as e:
        logger.error("Ошибка при проверке статуса пользователя: %s", e, exc_info=True)
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
        f"🔑 Статус: {status_text}\n\n"
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


# Обработчик для кнопки "Супер!"
@router.callback_query(lambda c: c.data == "super")
async def handle_super_button(callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
    bot = callback_query.bot

    # Отправляем "Пупер!"
    await bot.send_message(chat_id=chat_id, text="Пупер!")
    await callback_query.answer()  # Закрываем уведомление о нажатии кнопки

    # Задержка в 2 секунды перед отправкой главного меню
    await asyncio.sleep(2)
    await show_main_menu(chat_id, bot)
