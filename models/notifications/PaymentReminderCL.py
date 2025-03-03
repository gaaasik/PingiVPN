import asyncio
import json
import logging
import os
import traceback
from datetime import datetime, timedelta
from typing import List

import aiosqlite
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from communication_with_servers.handler_unknown_server_queue import process_unknown_server_queue
from models.UserCl import UserCl
from models.notifications.NotificationBaseCL import NotificationBase
from models.notifications.utils.dates import is_trial_ended
from bot.handlers.admin import send_admin_log, ADMIN_CHAT_IDS  # Функция отправки сообщения админу
from bot_instance import bot  # Инстанс бота для отправки сообщений

SEREVERS_IP = [
    "185.104.112.64",    # Server_1000
    "194.135.38.128",    # Server_2000
    "90.156.228.68",     # Server_3000
    "194.87.220.216",    # Server_4000
    "87.249.50.108",     # Server_5000
    "217.151.231.215",   # Server_6000
    "194.35.119.227",    # Server_7000
    "92.51.46.66",       # Server_8000
    "194.35.116.119",    # Server_9000
    "88.218.169.126",    # Server_10000
    "147.45.137.180",    # Server_11000
    "88.218.169.80",     # Server_12000
    "194.87.49.144",     # Server_13000
    "89.23.119.110",     # Server_14000
    "85.92.108.52",      # Server_15000
    "194.87.250.200",    # Server_16000
    "147.45.225.175",    # Server_17000
    "185.201.28.16",     # Server_18000
    "147.45.142.205",    # Server_19000
    "147.45.232.240",    # Server_10
    "217.25.91.109",     # Server_Bot_100
    "147.45.234.70",     # Server_21000
    "194.58.57.88",      # Server_22000
    "194.87.134.170",    # Server_23000
    "141.98.235.50",     # Server_24000
    "194.164.216.197",   # Server_25000
    "80.209.243.248",    # USA_27000
    "195.26.231.178",    # Germany_28000
    "66.248.207.185",    # NL_29000
    "195.26.230.208",    # FIN_31000
    "176.222.53.29",     # NL_32000
    "5.39.220.237",      # NL_33000
]




class PaymentReminder(NotificationBase):

    async def fetch_target_users(self) -> List[int]:
        """
        Получение пользователей, у которых завершён пробный период и требуется оплата.
        """
        query = """
        SELECT chat_id
        FROM users_key
        WHERE value_key IS NOT NULL
        AND value_key != ''
        AND json_valid(value_key) = 1
        AND json_extract(value_key, '$[0].enable') = 1
        AND json_extract(value_key, '$[0].date_key_off') IS NOT NULL
        AND json_extract(value_key, '$[0].date_key_off') != ''
        AND datetime(
            substr(json_extract(value_key, '$[0].date_key_off'), 7, 4) || '-' ||
            substr(json_extract(value_key, '$[0].date_key_off'), 4, 2) || '-' ||
            substr(json_extract(value_key, '$[0].date_key_off'), 1, 2) || ' ' ||
            substr(json_extract(value_key, '$[0].date_key_off'), 12, 8)
        ) < datetime('now');
        """

        blocked_users = []
        try:
            logging.info("🔍 Тестируем SQL-запрос перед выполнением...")
            logging.info(f"Запрос:\n{query}")

            async with aiosqlite.connect(os.getenv('database_path_local')) as db:
                async with db.execute(query) as cursor:
                    rows = await cursor.fetchall()

            logging.info(f"✅ SQL-запрос выполнен! Найдено записей: {len(rows)}")

            # Выводим первых 5 записей для отладки
            for row in rows[:5]:
                logging.info(f"👤 Найден пользователь: chat_id={row[0]}")

            # Сохраняем всех найденных пользователей
            blocked_users = [row[0] for row in rows]

            for user in blocked_users:
                us = await UserCl.load_user(user)
                await us.active_server.enable.set(False)

            ###### Толя добавил #########################################################################################################
            await process_unknown_server_queue()
            #########################################################################################################################

            # Логирование количества заблокированных пользователей
            if blocked_users:
                await send_admin_log(bot, f"🔔 {len(blocked_users)} пользователей нуждаются в уведомлении об оплате.")
            else:
                await send_admin_log(bot, "🔔 Нет пользователей для уведомления о блокировке доступа.")

        except Exception as e:
            logging.error(f"❌ Ошибка при выполнении SQL-запроса: {e}")
            logging.error(traceback.format_exc())

        return blocked_users

    def get_message_template(self) -> str:
        """
        Шаблон сообщения для уведомления о блокировке доступа.
        """
        return (
            "❌ <b>Ваш доступ заблокирован</b>.\n\n"
            "Для продолжения использования VPN, пожалуйста, продлите подписку:\n\n"
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
