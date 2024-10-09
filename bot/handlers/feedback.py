import logging

from aiogram import Router, types, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.handlers.admin import ADMIN_CHAT_IDS
from bot.utils.db import set_feedback_status  # Ваша функция для обновления статуса
#from main import send_admin_log  # Ваша функция для отправки сообщения админу

router = Router()
async def send_admin_log(bot: Bot, message: str):
    """Отправка сообщения админу и запись в лог"""
    try:
        await bot.send_message(chat_id=ADMIN_CHAT_IDS, text=message)
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения админу: {e}")

# Обработчик для кнопки "Отлично"
@router.callback_query(lambda call: call.data == "feedback_excellent")
async def feedback_excellent_handler(callback_query: types.CallbackQuery):
    chat_id = callback_query.from_user.id
    bot = callback_query.bot

    # Обновляем статус на "excellent"
    await set_feedback_status(bot, chat_id, "excellent")

    # Отправляем сообщение админу
    await send_admin_log(bot, f"Пользователь с ID {chat_id} нажал кнопку 'Отлично'")

    # Отправляем пользователю подтверждение
    await callback_query.answer("Спасибо за ваш отзыв!", show_alert=True)

# Обработчик для кнопки "Плохо"
@router.callback_query(lambda call: call.data == "feedback_bad")
async def feedback_bad_handler(callback_query: types.CallbackQuery):
    chat_id = callback_query.from_user.id
    bot = callback_query.bot

    # Обновляем статус на "bad"
    await set_feedback_status(bot, chat_id, "bad")

    # Отправляем сообщение админу
    await send_admin_log(bot, f"Пользователь с ID {chat_id} нажал кнопку 'Плохо'")

    # Отправляем пользователю подтверждение
    await callback_query.answer("Мы примем ваш отзыв во внимание!", show_alert=True)
