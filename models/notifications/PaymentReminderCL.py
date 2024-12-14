import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import List

import aiosqlite
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from models.UserCl import UserCl
from models.notifications.NotificationBaseCL import NotificationBase
from models.notifications.utils.dates import is_trial_ended
from bot.handlers.admin import send_admin_log, ADMIN_CHAT_IDS  # Функция отправки сообщения админу
from bot_instance import bot  # Инстанс бота для отправки сообщений
SEREVERS_IP = ["87.249.50.108","217.151.231.215","194.35.119.227","90.156.228.68","92.51.46.66","194.35.116.119","88.218.169.126","147.45.137.180","88.218.169.80","194.87.49.144"]


async def filter_users_with_unpaid_access(batch: List[int]) -> List[int]:
    """
    Фильтрует пользователей, чей пробный период завершился и подписка не оплачена.
    """
    blocked_users = []

    async def check_user(chat_id: int):
        try:
            user = await UserCl.load_user(chat_id)
            if not user or not user.servers:
                return None

            for server in user.servers:
                date_key_off = await server.date_key_off.get()
                has_paid_key = await server.has_paid_key.get()
                server_ip = await server.server_ip.get()
                is_enabled = await server.enable.get()
                # Проверяем, завершился ли пробный период, подписка не оплачена а статус работы true
                if await is_trial_ended(date_key_off) and has_paid_key == 0 and server_ip in SEREVERS_IP and is_enabled:
                    # Блокируем доступ
                    #await server.enable.set(False)
                    return chat_id
        except Exception as e:
            print(f"Ошибка при обработке пользователя {chat_id}: {e}")
            return None

    results = await asyncio.gather(*(check_user(chat_id) for chat_id in batch))
    blocked_users = [chat_id for chat_id in results if chat_id is not None]
    print(blocked_users)
    return blocked_users


class PaymentReminder(NotificationBase):

    async def fetch_target_users(self) -> List[int]:
        """
        Получение пользователей, у которых завершён пробный период и требуется оплата.
        """
        all_users = await UserCl.get_all_users()
        blocked_users = []
        for batch in self.split_into_batches(all_users):
            blocked_users.extend(await filter_users_with_unpaid_access(batch))

        # Логирование количества заблокированных пользователей
        try:
            if blocked_users:
                await send_admin_log(bot, f"🔔 {len(blocked_users)} пользователей нуждаются в уведомлении об оплате.")
            else:
                await send_admin_log(bot, "🔔 Нет пользователей для уведомления о блокировке доступа.")
        except Exception as e:
            print(f"Ошибка при отправке сообщения админу: {e}")

        return blocked_users

    def get_message_template(self) -> str:
        """
        Шаблон сообщения для уведомления о блокировке доступа.
        """
        return (
            "❌ <b>Ваш доступ заблокирован</b>.\n\n"
            "Пробный период завершён. Для продолжения использования VPN, пожалуйста, оформите подписку:\n\n"
            "💳 <b>Оплатите доступ</b> и наслаждайтесь безопасным соединением без ограничений."
        )

    def get_keyboard(self) -> InlineKeyboardMarkup:
        """
        Клавиатура для сообщения об оплате.
        """
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💳 Оплатить доступ", callback_data="buy_vpn")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ]
        )
        return keyboard

    async def after_send_success(self, user_id: int):
        """
        Действия после успешной отправки уведомления:
        1. Смена статуса пользователя, если пробный период истёк.
        2. Запись логов об отправке уведомления в базу данных.
        """
        today = datetime.now().strftime("%m_%d")  # Формат мм_дд
        notification_type = f"notification_{today}"

        try:
            # Загрузка пользователя
            user = await UserCl.load_user(user_id)

            if not user:
                logging.error(f"Пользователь {user_id} не найден для обновления статуса.")
                return

            # # Обновляем статус сервера, если пробный период истёк
            # for server in user.servers:
            #     date_key_off = await server.date_key_off.get()
            #     if datetime.strptime(date_key_off, "%d.%m.%Y %H:%M:%S") < datetime.now():
            #         await server.enable.set(False)  # Блокируем доступ

            # Логируем уведомление в базу данных
            async with aiosqlite.connect(os.getenv('database_path_local')) as db:
                # Читаем текущие данные логов
                query = "SELECT notification_data FROM notifications WHERE chat_id = ?"
                async with db.execute(query, (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    notification_data = json.loads(row[0]) if row and row[0] else {}

                # Обновляем данные логов
                notification_data[notification_type] = {
                    "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "sent",
                    "message_type": "payment_reminder"
                }

                # Обновляем запись в базе данных
                update_query = "UPDATE notifications SET notification_data = ? WHERE chat_id = ?"
                await db.execute(update_query, (json.dumps(notification_data), user_id))
                await db.commit()

            logging.info(f"Уведомление успешно отправлено и логировано для пользователя {user_id}.")

        except Exception as e:
            logging.error(f"Ошибка при обработке пользователя {user_id} в after_send_success: {e}")
