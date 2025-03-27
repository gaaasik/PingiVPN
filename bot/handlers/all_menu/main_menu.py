import asyncio

from aiogram import Router, types, Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from bot.handlers.cleanup import delete_unimportant_messages, store_message, messages_for_db, register_message_type
import os

from bot.states.StatesCL import GeneralStates
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
        active_server = us.active_server

        if count_key == 0 or not active_server:
            # Если ключей нет
            logger.info("У пользователя нет ключей. Возвращаем сообщение о подключении VPN.")
            return f"Нажмите *Подключить VPN*\n"

        # Проверяем статус первого ключа
        status_key = await us.active_server.status_key.get()
        enabled = await us.active_server.enable.get()
        has_paid_key = await us.active_server.has_paid_key.get()
        end_date_str = await us.active_server.date_key_off.get_date()

        # Парсим строку даты в объект datetime для расчётов
        try:
            end_date = datetime.strptime(end_date_str, "%d.%m.%Y")
        except ValueError as date_error:
            logger.error(f"Ошибка преобразования строки даты {end_date_str} в объект datetime: {date_error}")
            return "Неверный формат даты ключа. Обратитесь в поддержку."

        # Рассчитываем оставшиеся дни
        today = datetime.now()
        remaining_days = (end_date - today).days
        # Формируем текст статуса в зависимости от статуса ключа
        if (enabled == True) and (has_paid_key == 0) and remaining_days > 0:
            return f"Пробный период до {end_date_str} (осталось {remaining_days} дней)"

        elif enabled == False or remaining_days < 0:
            return ("Ключ заблокирован, требуется оплата")

        elif (enabled == True) and (has_paid_key > 0):
            expiration_text = ""
            if remaining_days < 0:
                expiration_text = f"Требуется оплата"
            else:
                expiration_text = f"Ключ активен до {end_date_str} (осталось {remaining_days} дней)"

            return expiration_text


        else:
            logger.warning(f"Неизвестный статус ключа: {status_key}")
            return "Статус ключа не распознан"

    except Exception as e:
        logger.error("Ошибка при проверке статуса пользователя: %s", e, exc_info=True)
        return "Произошла ошибка при проверке статуса. Попробуйте позже."


async def show_main_menu(chat_id: int, bot: Bot, edit=False, message=None):
    us = await UserCl.load_user(chat_id)
    if not us:
        await bot.send_message(chat_id, "Для начала нажмите /start")
        return

    user_name_full = await us.user_name_full.get()
    user_name = await us.user_login.get()
    status_text = await get_user_status_text(us)
    days_text = await get_count_days_since_registration(us)

    text = (
        f"Привет {user_name_full}! 🕶\n\n"
        "PingiVPN — быстрый и безопасный интернет без ограничений:\n\n"
        "📱 Доступ к соцсетям\n"
        "🛡 Анонимность\n"
        "📶 Устойчивость к блокировкам\n"
        "🚀 Высокая скорость\n"
        "💻 Все устройства\n\n"
        f"🔑 Статус: *{status_text}*\n\n"
        f"{days_text}"
    )

    if edit and message:
        await message.edit_text(text, reply_markup=main_menu_inline_keyboard(), parse_mode="Markdown")
    else:
        await bot.send_message(chat_id=chat_id, text=text, reply_markup=main_menu_inline_keyboard(), parse_mode="Markdown")




@router.message(F.text == "🏠 Главное меню")
@router.message(Command(commands=["menu"]))
@router.callback_query(F.data == "main_menu")
async def handle_main_menu(event: types.Message | types.CallbackQuery, state: FSMContext):
    await state.set_state(GeneralStates.main_menu)

    if isinstance(event, types.CallbackQuery):
        await event.answer()
        await show_main_menu(
            chat_id=event.message.chat.id,
            bot=event.bot,
            edit=True,
            message=event.message
        )
    elif isinstance(event, types.Message):
        try:
            await event.delete()
        except Exception:
            pass  # Иногда сообщение не удаляется (например, от бота)

        await show_main_menu(
            chat_id=event.chat.id,
            bot=event.bot,
            edit=False  # Поскольку edit невозможно без message
        )


# Обработчик для кнопки "Супер!"
@router.callback_query(lambda c: c.data == "super")
async def handle_super_button(callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
    bot = callback_query.bot

    # Отправляем "Пупер!"
    await bot.send_message(chat_id=chat_id, text="Пупер!")
    await callback_query.answer()  # Закрываем уведомление о нажатии кнопки

    # Задержка в 2 секунды перед отправкой главного меню
    await asyncio.sleep(1)
    await show_main_menu(chat_id, bot)
