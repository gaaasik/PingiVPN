import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import List
import logging

import aiosqlite
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

from models.UserCl import UserCl
from .NotificationBaseCL import NotificationBase
load_dotenv()
class CompensationNotification(NotificationBase):
    def __init__(self, batch_size: int = 50):
        super().__init__(batch_size)

    async def fetch_target_users(self) -> List[int]:
        """
        Выборка пользователей, подходящих под критерии компенсации.
        """
        all_users = await UserCl.get_all_users()
        target_users = []

        async def  check_and_update_user(chat_id: int):
            try:
                user = await UserCl.load_user(chat_id)
                if user and user.servers:
                    server = user.servers[0]  # Берём первый сервер пользователя
                    # не тестировал

                    # Проверяем, отправлялось ли уже уведомление с типом "compensation"
                    async with aiosqlite.connect(os.getenv('database_path_local')) as db:
                        query = "SELECT notification_data FROM notifications WHERE chat_id = ?"
                        async with db.execute(query, (chat_id,)) as cursor:
                            row = await cursor.fetchone()
                            if row and row[0]:
                                notification_data = json.loads(row[0])
                                for key, notification in notification_data.items():
                                    if notification.get("message_type") == "compensation" and notification.get(
                                            "status") == "sent":
                                        logging.info(
                                            f"Уведомление 'compensation' уже отправлено пользователю {chat_id}. Пропускаем.")
                                        return None

                    # Получаем необходимые данные
                    date_payment_key = await server.date_payment_key.get()
                    has_paid_key = await server.has_paid_key.get()

                    # Проверяем, что date_payment_key не является None или некорректным
                    if not date_payment_key or date_payment_key in ["null", "NULL"]:
                        logging.error(
                            f"Некорректное значение date_payment_key для пользователя {chat_id}: {date_payment_key}")
                        return None

                    # Проверяем, что has_paid_key валиден
                    if has_paid_key is None or int(has_paid_key) <= 0:
                        #logging.error(f"Некорректное значение has_paid_key для пользователя {chat_id}: {has_paid_key}")
                        return None

                    # Проверяем условия
                    try:
                        date_payment_key_dt = datetime.strptime(date_payment_key, "%d.%m.%Y %H:%M:%S")
                    except ValueError as e:
                        logging.error(f"Ошибка при конвертации даты для пользователя {chat_id}: {e}")
                        return None

                    if date_payment_key_dt <= datetime(2024, 12, 20) and has_paid_key > 0:
                        await self.update_user_date_key_off(chat_id)
                        return chat_id
            except Exception as e:
                logging.error(f"Ошибка при обработке пользователя {chat_id}: {e}")
            return None

        results = await asyncio.gather(*(check_and_update_user(chat_id) for chat_id in all_users))
        target_users = [user for user in results if user is not None]
        return target_users

    async def update_user_date_key_off(self, chat_id: int):
        """
        Обновление даты окончания доступа пользователя на +10 дней.
        """
        try:
            user = await UserCl.load_user(chat_id)
            if user and user.servers:
                server = user.servers[0]  # Берём первый сервер пользователя

                current_date_key_off = await server.date_key_off.get()
                new_date_key_off = datetime.strptime(current_date_key_off, "%d.%m.%Y %H:%M:%S") + timedelta(days=10)

                # Устанавливаем новую дату
                #await server.date_key_off.set(new_date_key_off.strftime("%d.%m.%Y %H:%M:%S"))

                logging.info(f"Дата продления {current_date_key_off} обновлена для пользователя {chat_id}: {new_date_key_off}")
        except Exception as e:
            logging.error(f"Ошибка при обновлении даты для пользователя {chat_id}: {e}")

    def get_message_template(self) -> str:
        """
        Шаблон сообщения для уведомления о компенсации.
        """
        return (
            "⭐ <b>Добрый день!</b>\n\n"
            "💡 В связи с атаками на наши серверы у вас могли быть проблемы с подключением. "
            "Мы добавляем вам <b>дополнительно 10 дней доступа</b> в качестве компенсации. 🎉\n\n"
            "Спасибо, что остаетесь с нами!\n"
            "💌 Хорошего вам дня!"
        )

    def get_keyboard(self) -> InlineKeyboardMarkup:
        """
        Клавиатура для уведомления.
        """
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
            [InlineKeyboardButton(text="🙏 Спасибо!", callback_data="thank_you")]
        ])
        return keyboard

    async def after_send_success(self, user_id: int):
        """
        Действия после успешной отправки уведомления:
        Запись логов об отправке уведомления в базу данных.
        """
        today = datetime.now().strftime("%m_%d")  # Формат мм_дд
        notification_type = f"compensation_notification_{today}"

        try:
            user = await UserCl.load_user(user_id)

            if not user:
                logging.error(f"Пользователь {user_id} не найден для обновления статуса.")
                return

            async with aiosqlite.connect(os.getenv('database_path_local')) as db:
                query = "SELECT notification_data FROM notifications WHERE chat_id = ?"
                async with db.execute(query, (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    notification_data = json.loads(row[0]) if row and row[0] else {}

                notification_data[notification_type] = {
                    "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "sent",
                    "message_type": "compensation"
                }

                update_query = "UPDATE notifications SET notification_data = ? WHERE chat_id = ?"
                await db.execute(update_query, (json.dumps(notification_data), user_id))
                await db.commit()

            logging.info(f"Уведомление о компенсации успешно отправлено и логировано для пользователя {user_id}.")

        except Exception as e:
            logging.error(f"Ошибка при обработке пользователя {user_id} в after_send_success: {e}")
