import aiosqlite
from datetime import datetime
import logging
from aiogram import Bot
import os

from bot.handlers.admin import ADMIN_CHAT_IDS
from bot.handlers.cleanup import message_types_mapping, delete_message_with_type, store_message
from bot.handlers.status import generate_status_message


# Обработка действий после успешной оплаты
async def handle_post_payment_actions(bot: Bot, chat_id: int):
    """Выполняет действия после успешной оплаты."""

    # Удаление сообщений об оплате (здесь можно вставить свой код)
    # Например:
    await delete_message_with_type(chat_id, "msg_with_pay_url", bot)
    await delete_message_with_type(chat_id, "account_status", bot)

    # Отправка сообщения пользователю
    try:
        sent_message = await bot.send_message(
            chat_id=chat_id,
            text=f"Спасибо за оплату. Ваш платеж успешно заверешен.\n Ваша подписка активна"
        )

        # Вызов функции для генерации сообщения о статусе и клавиатуры.
        status_message, keyboard = await generate_status_message(chat_id)

        # Отправка сообщения с информацией о статусе пользователя и клавиатурой.
        await bot.send_message(
            chat_id=chat_id,
            text=status_message,
            parse_mode="Markdown",  # Указываем, что текст должен использовать Markdown для форматирования.
            reply_markup=keyboard  # Передаем сгенерированную клавиатуру.
        )

        logging.info(f"Сообщение пользователю {chat_id} об успешной оплате отправлено.")
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения пользователю {chat_id}: {e}")

    # Отправка уведомлений администраторам
    for admin_chat_id in ADMIN_CHAT_IDS:
        try:
            await bot.send_message(
                chat_id=admin_chat_id,
                text=f"Уведомление администратору: пользователь с ID {chat_id} успешно оплатил подписку."
            )
            logging.info(f"Уведомление об оплате отправлено администратору {admin_chat_id}.")
        except Exception as e:
            logging.error(f"Ошибка при отправке уведомления администратору {admin_chat_id}: {e}")
