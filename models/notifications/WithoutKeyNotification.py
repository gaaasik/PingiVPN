import json
import logging
import os
import random
import traceback
from datetime import datetime
from typing import List

import aiosqlite
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from models.notifications.NotificationBaseCL import NotificationBase
from bot.handlers.admin import send_admin_log
from bot_instance import bot


class WithoutKeyNotification(NotificationBase):
    async def fetch_target_users(self) -> List[int]:
        """
        Выбирает пользователей, у которых ещё нет VPN-ключа (value_key пустой или невалидный).
        """
        query = """
        SELECT u.chat_id
        FROM users u
        LEFT JOIN users_key uk ON uk.chat_id = u.chat_id
        WHERE IFNULL(u.active_chat, 1) = 1
          AND (uk.value_key IS NULL OR uk.value_key = '' OR NOT json_valid(uk.value_key));
        """
        try:
            async with aiosqlite.connect(os.getenv('database_path_local')) as db:
                async with db.execute(query) as cursor:
                    rows = await cursor.fetchall()
                    target_users = [row[0] for row in rows]

            await send_admin_log(bot, f"📌 Найдено {len(target_users)} пользователей без созданного ключа.")
            return target_users

        except Exception as e:
            logging.error(f"Ошибка при выборке пользователей (WithoutKeyNotification): {e}")
            logging.error(traceback.format_exc())
            return []

    def get_message_template(self) -> str:
        templates = [
            "🧠 <b>Не получилось подключиться?</b>\n\n"
            "Сервис работает стабильно и стоит всего 199₽. А <b>первые 7 дней бесплатно</b> — без рисков!\n"
            "Уже тысячи пользователей подключились за минуту. \n Нажмите кнопку, если нужна помощь 💬",

            "🧰 <b>Трудности с настройкой?</b>\n\n"
            "Ничего страшного — мы <b>поможем вручную</b>.\n"
            "VPN работает отлично и стоит меньше чашки кофе ☕. Первые 7 дней — <b>бесплатно</b>!"
            "\n Нажмите кнопку, если нужна помощь 💬",

            "🧡 <b>Вы ещё не начали пользоваться VPN?</b>\n\n"
            "Больше 2000 пользователей уже подключились за 199₽ и наслаждаются свободным интернетом.\n"
            "<b>Попробуйте бесплатно</b> — если понравится сделаем скидку 🔥",

            "🎯 <b>Не смогли подключить VPN?</b>\n\n"
            "Мы рядом — <b>поможем всё настроить вручную</b>. Нажмите на кнопку и напишите нам.\n"
            "<b>7 дней бесплатно</b> и всего 199₽ в месяц — лучшее предложение на рынке 🔥"
        ]

        return random.choice(templates)

    def get_keyboard(self) -> InlineKeyboardMarkup:

        buttons = [
            [InlineKeyboardButton(text="🔌 Подключить VPN",  callback_data="connect_vpn")],
            [InlineKeyboardButton(text="💬 Связаться с нами",url="https://t.me/pingi_help")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    async def after_send_success(self, user_id: int):
        """ продлить доступ
        Логирует успешную отправку уведомления в таблицу notifications.
        """
        today = datetime.now().strftime("%m_%d")
        notification_type = f"without_key_notification_{today}"

        try:
            async with aiosqlite.connect(os.getenv('database_path_local')) as db:
                query = "SELECT notification_data FROM notifications WHERE chat_id = ?"
                async with db.execute(query, (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    notification_data = json.loads(row[0]) if row and row[0] else {}

                notification_data[notification_type] = {
                    "sent_at": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                    "status": "sent",
                    "message_type": "without_key"
                }

                update_query = "UPDATE notifications SET notification_data = ? WHERE chat_id = ?"
                await db.execute(update_query, (json.dumps(notification_data), user_id))
                await db.commit()
            #Лишний лог
            #logging.info(f"✅ WithoutKeyNotification отправлен пользователю {user_id}")
        except Exception as e:
            logging.error(f"Ошибка при after_send_success для {user_id}: {e}")
