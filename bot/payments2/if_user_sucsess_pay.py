import aiosqlite
from datetime import datetime
import logging
from aiogram import Bot
import os

from bot.handlers.admin import ADMIN_CHAT_IDS


# Асинхронное обновление подписки
async def update_user_subscription_db(user_id: int):
    """Асинхронно обновляет статус подписки пользователя в базе данных."""
    db_path = os.getenv('database_path_local')  # Путь к базе данных

    try:
        # Устанавливаем соединение с базой данных
        async with aiosqlite.connect(db_path) as conn:
            await conn.execute("""
                UPDATE users
                SET subscription_status = 'active',
                    has_paid_subscription = 1,
                    vpn_usage_start_date = ?
                WHERE chat_id = ?
            """, (datetime.now(), user_id))
            # Сохраняем изменения
            await conn.commit()
            logging.info(f"Подписка обновлена для пользователя с ID {user_id}.")
    except Exception as e:
        logging.error(f"Ошибка при обновлении подписки для пользователя с ID {user_id}: {e}")


# Обработка действий после успешной оплаты
async def handle_post_payment_actions(bot: Bot, chat_id: int):
    """Выполняет действия после успешной оплаты."""

    # Удаление сообщений об оплате (здесь можно вставить свой код)
    # Например:
    # await bot.delete_message(chat_id, message_id)

    # Отправка сообщения пользователю
    try:
        await bot.send_message(
            chat_id=chat_id,
            text="Спасибо за оплату! Ваша подписка активна."
        )
        logging.info(f"Сообщение пользователю {chat_id} об успешной оплате отправлено.")
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения пользователю {chat_id}: {e}")

    # Отправка уведомлений администраторам
    for admin_chat_id in ADMIN_CHAT_IDS:
        try:
            await bot.send_message(
                chat_id=admin_chat_id,
                text=f"Пользователь с ID {chat_id} успешно оплатил подписку."
            )
            logging.info(f"Уведомление об оплате отправлено администратору {admin_chat_id}.")
        except Exception as e:
            logging.error(f"Ошибка при отправке уведомления администратору {admin_chat_id}: {e}")
