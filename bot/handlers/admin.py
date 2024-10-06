import logging

from aiogram import Bot

from bot.handlers.user_help_request import ADMIN_CHAT_ID

# ID администратора
ADMIN_CHAT_ID = 456717505

async def send_admin_log(bot: Bot, message: str):
    """Отправка сообщения админу и запись в лог"""
    try:
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=message)
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения админу: {e}")
