import logging

from aiogram import Bot

# Список администраторов
ADMIN_CHAT_IDS = [456717505]#, 1388513042]  # Укажи ID администраторов


async def send_admin_log(bot: Bot, message: str):
    for admin_chat_id in ADMIN_CHAT_IDS:
        try:
            await bot.send_message(chat_id=admin_chat_id, text=message)
            logging.info(f"Сообщение отправлено админу с ID {admin_chat_id}: {message}")
        except Exception as e:
            logging.error(f"Ошибка при отправке сообщения админу с ID {admin_chat_id}: {e}")
