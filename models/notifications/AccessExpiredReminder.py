import asyncio
import json
import logging
import os
import traceback
from datetime import datetime
from typing import List
import random

import aiosqlite
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from models.notifications.NotificationBaseCL import NotificationBase
from bot.handlers.admin import send_admin_log
from bot_instance import bot


class AccessExpiredReminder(NotificationBase):

    async def fetch_target_users(self) -> List[int]:
        """
        Получает пользователей с отключённым доступом,
        у которых date_key_off от 1 до 5 дней назад и активный чат.
        """
        query = """
        SELECT uk.chat_id
        FROM users_key uk
        JOIN users u ON u.chat_id = uk.chat_id
        WHERE uk.value_key IS NOT NULL
          AND uk.value_key != ''
          AND json_valid(uk.value_key) = 1
          AND json_extract(uk.value_key, '$[0].date_key_off') IS NOT NULL
          AND json_extract(uk.value_key, '$[0].date_key_off') != ''
          AND IFNULL(u.active_chat, 1) = 1
          AND date(
                substr(json_extract(uk.value_key, '$[0].date_key_off'), 7, 4) || '-' ||
                substr(json_extract(uk.value_key, '$[0].date_key_off'), 4, 2) || '-' ||
                substr(json_extract(uk.value_key, '$[0].date_key_off'), 1, 2)
          ) BETWEEN date('now', '-5 days') AND date('now', '-1 days');
        """

        try:
            async with aiosqlite.connect(os.getenv('database_path_local')) as db:
                async with db.execute(query) as cursor:
                    rows = await cursor.fetchall()
                    target_users = [row[0] for row in rows]

            await send_admin_log(bot, f"📌 Найдено {len(target_users)} пользователей с истёкшим доступом (1–5 дней назад).")
            return target_users

        except Exception as e:
            logging.error(f"Ошибка в выборке пользователей: {e}")
            logging.error(traceback.format_exc())
            return []

    def get_message_template(self) -> str:
        """
        Возвращает случайный шаблон уведомления из 5 заранее заданных.
        """
        templates = [
            "😢 <b>Мы приостановили доступ к вашему VPN</b>\n\n"
            "Но хорошая новость — его можно восстановить прямо сейчас, в 1 клик!\n"
            "Вернитесь — и наслаждайтесь безопасным интернетом без ограничений. 🧡",

            "⚡ <b>VPN ждёт вас!</b>\n\n"
            "Забудьте о блокировках. YouTube, Instagram, TikTok — всё снова откроется на максимальной скорости с VPN.\n"
            "Подключайтесь за 1 минуту. 🚀",

            "🎁 <b>Получите бесплатный доступ в подарок!</b>\n\n"
            "Если пригласите друга, вы получите бонусные дни доступа. Без лишних шагов. Просто нажмите кнопку ниже! 🎉",

            "🌍 <b>Ваш интернет, ваши правила</b>\n\n"
            "Безопасный доступ ко всем сайтам, даже если они заблокированы. Мы сохранили все настройки — просто подключитесь снова.",

            "🦸 <b>Вы тут без VPN?</b>\n\n"
            "Скорость, анонимность, 4K видео — всё вернётся, если нажмёте пару кнопок.\n"
            "Не ждите блокировок — будьте готовы заранее! 🔐"
        ]

        return random.choice(templates)

    def get_keyboard(self) -> InlineKeyboardMarkup:
        buttons = [
            [InlineKeyboardButton(text="💳 Продлить доступ", callback_data="buy_vpn")],
            [InlineKeyboardButton(text="🧩 Розыгрыш", callback_data="lottery_entry"),
             InlineKeyboardButton(text="✍️ Оставить отзыв", callback_data="leave_feedback")],
            [InlineKeyboardButton(text="🔗 Поделится с другом", callback_data="show_referral_link")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    async def after_send_success(self, user_id: int):
        """
        Логирует успешную отправку уведомления в таблицу notifications.
        """
        today = datetime.now().strftime("%m_%d")
        notification_type = f"access_expired_reminder_{today}"

        try:
            async with aiosqlite.connect(os.getenv('database_path_local')) as db:
                query = "SELECT notification_data FROM notifications WHERE chat_id = ?"
                async with db.execute(query, (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    notification_data = json.loads(row[0]) if row and row[0] else {}

                notification_data[notification_type] = {
                    "sent_at": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                    "status": "sent",
                    "message_type": "access_expired"
                }

                update_query = "UPDATE notifications SET notification_data = ? WHERE chat_id = ?"
                await db.execute(update_query, (json.dumps(notification_data), user_id))
                await db.commit()

            logging.info(f"✅ AccessExpiredReminder отправлен для пользователя {user_id}")
        except Exception as e:
            logging.error(f"Ошибка при after_send_success для {user_id}: {e}")
