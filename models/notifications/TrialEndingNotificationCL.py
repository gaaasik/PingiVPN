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


class TrialEndingNotification(NotificationBase):
    def __init__(self, batch_size: int = 50):
        super().__init__(batch_size)

    async def fetch_target_users(self) -> List[int]:
        """
        Получение пользователей, чей пробный период завершён.
        """
        print("Начинается выборка пользователей для уведомления...")
        try:
            all_users = await UserCl.get_all_users()
            print(f"Всего пользователей: {len(all_users)}")

            # Фильтруем пользователей
            filtered_users = []
            for batch in self.split_into_batches(all_users):
                filtered_users.extend(await self.filter_users_with_expired_trials(batch))

            # Логируем результат
            if filtered_users:
                await send_admin_log(bot,
                                     f"Нужно уведомить {len(filtered_users)} пользователей о завершении пробного периода.")
            else:
                await send_admin_log(bot, "Нет пользователей для уведомления о завершении пробного периода.")

            return filtered_users
        except Exception as e:
            logging.error(f"Ошибка при выборке пользователей: {e}")
            return []

    async def filter_users_with_expired_trials(self, batch: List[int]) -> List[int]:
        """
        Фильтруем пользователей, чей пробный период завершён.
        """
        expiring_users = []

        async def check_user(chat_id: int):
            try:
                user = await UserCl.load_user(chat_id)
                if not user or not user.servers:
                    print(f"Пользователь {chat_id} не имеет серверов. Пропускаем.")
                    return None

                for server in user.servers:
                    date_key_off = await server.date_key_off.get()
                    has_paid_key = await server.has_paid_key.get()

                    # Преобразуем дату окончания в объект datetime
                    trial_end_date = datetime.strptime(date_key_off, "%d.%m.%Y %H:%M:%S")

                    # Проверяем, если пробный период завершён (на 1 день меньше текущей даты)
                    if (trial_end_date + timedelta(days=1)).date() < datetime.now().date() and has_paid_key == 0:
                        print(f"Пользователь {chat_id} должен быть уведомлён.")
                        return chat_id
            except Exception as e:
                print(f"Ошибка при обработке пользователя {chat_id}: {e}")
                return None

        # Асинхронная проверка всех пользователей в батче
        results = await asyncio.gather(*(check_user(chat_id) for chat_id in batch))
        expiring_users = [chat_id for chat_id in results if chat_id is not None]
        return expiring_users

    def get_message_template(self) -> str:
        """
        Шаблон сообщения для уведомления о завершении пробного периода.
        """
        return (
            "⏳ <b>Время истекло! Продлите доступ к VPN</b> 🐧\n\n"
            "🥶 Ваш пробный период закончился, но вы всегда можете продлить доступ.\n"
            "💳 Оформите подписку, чтобы продолжить наслаждаться надёжным VPN.\n\n"
            "🎯 <b>Быстро. Просто. Без рекламы.</b>\n\n"
            "👥 <b>Продлите доступ бесплатно!</b>\n"
            "Пригласите друга и получите +3 дня.\n"
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
        Обновление статуса пользователя после успешной отправки уведомления.
        """
        today = datetime.now().strftime("%m_%d")  # Формат мм_дд
        notification_type = f"request_payment_{today}"

        query = "SELECT notification_data FROM notifications WHERE chat_id = ?"
        try:
            async with aiosqlite.connect(os.getenv('database_path_local')) as db:
                async with db.execute(query, (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    notification_data = json.loads(row[0]) if row and row[0] else {}

                # Обновляем JSON-данные
                notification_data[notification_type] = {
                    "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "sent"
                }

                # Записываем обратно в базу
                update_query = "UPDATE notifications SET notification_data = ? WHERE chat_id = ?"
                await db.execute(update_query, (json.dumps(notification_data), user_id))
                await db.commit()
        except Exception as e:
            logging.error(f"Ошибка при обновлении notification_data для пользователя {user_id}: {e}")
