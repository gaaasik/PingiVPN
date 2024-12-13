import asyncio
import os
from datetime import datetime, timedelta
from bot_instance import bot
from models.UserCl import UserCl
from .NotificationBaseCL import NotificationBase
from typing import List
import logging
import json
import aiosqlite
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.handlers.admin import send_admin_log
from .utils.dates import is_trial_ending_soon


class TrialEndingNotification(NotificationBase):
    def __init__(self, batch_size: int = 50):
        super().__init__(batch_size)

    async def fetch_target_users(self) -> List[int]:
        """
        Получение пользователей, у которых пробный период заканчивается через 1-2 дня.
        """
        try:
            all_users = await UserCl.get_all_users()
            expiring_users = []

            # Разделяем пользователей на батчи и фильтруем
            for batch in self.split_into_batches(all_users):
                expiring_users.extend(await self.filter_users_with_expired_trials(batch))

            # Логируем количество пользователей
            if expiring_users:
                await send_admin_log(bot,
                                     f"🔔 {len(expiring_users)} пользователей нуждаются в уведомлении о завершении пробного периода.")
            else:
                await send_admin_log(bot, "🔔 Нет пользователей для уведомления о завершении пробного периода.")

            return expiring_users
        except Exception as e:
            logging.error(f"Ошибка при выборке пользователей: {e}")
            return []

    async def is_trial_ending_soon(date_key_off: str, days_until_end: int = 2) -> bool:
        """
        Проверяет, заканчивается ли пробный период сегодня или через указанное количество дней.
        Если пробный период уже истёк, возвращает False.

        :param date_key_off: Строка с датой окончания в формате "%d.%m.%Y %H:%M:%S".
        :param days_until_end: Количество дней до окончания периода (по умолчанию 2).
        :return: True, если пробный период заканчивается сегодня или через days_until_end дней.
        """
        try:
            trial_end_date = datetime.strptime(date_key_off, "%d.%m.%Y %H:%M:%S")
            today = datetime.now()

            # Если пробный период уже истёк
            if trial_end_date.date() < today.date():
                return False

            # Если пробный период заканчивается сегодня или через days_until_end дней
            return today.date() <= trial_end_date.date() <= (today + timedelta(days=days_until_end)).date()
        except Exception as e:
            logging.error(f"Ошибка при проверке окончания пробного периода: {e}")
            return False

    async def filter_users_with_expired_trials(self, batch: List[int]) -> List[int]:
        """
        Фильтрует пользователей, у которых пробный период заканчивается через 1-2 дня,
        и проверяет, что уведомление `payment_reminder` ещё не отправлялось.
        """
        expiring_users = []

        async def has_payment_reminder_been_sent(user_id: int) -> bool:
            """
            Проверяет, было ли отправлено любое уведомление типа `payment_reminder`.

            :param user_id: ID пользователя.
            :return: True, если уведомление уже было отправлено, иначе False.
            """
            try:
                async with aiosqlite.connect(os.getenv('database_path_local')) as db:
                    query = "SELECT notification_data FROM notifications WHERE chat_id = ?"
                    async with db.execute(query, (user_id,)) as cursor:
                        row = await cursor.fetchone()
                        if row and row[0]:
                            notification_data = json.loads(row[0])
                            # Проверяем наличие `payment_reminder` среди уведомлений
                            for notification_key, notification_value in notification_data.items():
                                if notification_value.get(
                                        "message_type") == "payment_reminder" and notification_value.get(
                                    "status") == "sent":
                                    return True
                return False
            except Exception as e:
                logging.error(f"Ошибка при проверке уведомления `payment_reminder` для пользователя {user_id}: {e}")
                return False

        async def check_user(chat_id: int):
            try:
                user = await UserCl.load_user(chat_id)
                if not user or not user.servers:
                    return None

                for server in user.servers:
                    date_key_off = await server.date_key_off.get()
                    has_paid_key = await server.has_paid_key.get()

                    # Проверяем, заканчивается ли пробный период
                    if (
                            await is_trial_ending_soon(date_key_off, days_until_end=2)  # Пробный период заканчивается
                            and has_paid_key == 0  # Подписка не оплачена
                            and not await has_payment_reminder_been_sent(chat_id)  # Уведомление не отправлялось
                    ):
                        return chat_id
                return None
            except Exception as e:
                logging.error(f"Ошибка при обработке пользователя {chat_id}: {e}")
                return None

        results = await asyncio.gather(*(check_user(chat_id) for chat_id in batch))
        expiring_users = [chat_id for chat_id in results if chat_id is not None]
        return expiring_users

        # Параллельная проверка всех пользователей в батче
        results = await asyncio.gather(*(check_user(chat_id) for chat_id in batch))
        expiring_users = [chat_id for chat_id in results if chat_id is not None]
        return expiring_users

    def get_message_template(self) -> str:
        """
        Шаблон сообщения для уведомления о завершении пробного периода.
        """
        return (
            "⏳ <b>Осталось совсем чуть чуть!</b> 🐧\n\n"
            "🔐 <b>Продлите доступ к VPN прямо сейчас!</b>\n\n"
            "🥶 <b>Ваш пробный период скоро завершится.</b> Чтобы продолжить пользоваться нашим надёжным VPN:\n"
            "💳 Оформите подписку и наслаждайтесь безопасным и быстрым соединением.\n\n"
            "🎯 <b>Почему стоит остаться с нами?</b>\n"
            "✅ Высокая скорость\n"
            "✅ Полная анонимность\n"
            "✅ Без рекламы\n\n"
            "👥 <b>Хотите продлить доступ бесплатно?</b>\n"
            "Пригласите друга и получите <b>+3 дня</b>.\n"
            "Если ваш друг оформит подписку, вы получите <b>+14 дней</b> в подарок! 🎁"
        )

    def get_keyboard(self) -> InlineKeyboardMarkup:
        """
        Возвращает клавиатуру с кнопками для оплаты.
        """
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💳 Оплатить ключ", callback_data="buy_vpn")],
                [InlineKeyboardButton(text="🔗 Поделиться c другом", callback_data="show_referral_link")],
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
