import asyncio
import os
from datetime import datetime
from bot_instance import bot
from models.UserCl import UserCl
from .NotificationBaseCL import NotificationBase
from typing import List
import logging
import json
import aiosqlite
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from ..handlers.admin import send_admin_log


class UnsubscribedNotification(NotificationBase):
    def __init__(self, channel_username: str, batch_size: int = 50):
        super().__init__(batch_size)
        self.channel_username = channel_username

    async def fetch_target_users(self) -> List[int]:
        """
        Получение пользователей из базы данных, которые не подписаны на канал.
        """
        print("Начинается выборка пользователей...")
        try:
            # Получаем всех пользователей
            all_users = await UserCl.get_all_users()
            print(f"Всего пользователей: {len(all_users)}")

            # Фильтруем пользователей, проверяя наличие серверов и подписку
            filtered_users = []
            for batch in self.split_into_batches(all_users):
                filtered_users.extend(await self.filter_users_with_servers(batch))

            # Логирование количества неподписанных пользователей
            if filtered_users:
                await send_admin_log(bot, f"Не подписаны {len(filtered_users)} пользователей, сейчас будем отправлять им уведомления.")
            else:
                await send_admin_log(bot, "Все пользователи подписаны на канал, уведомлений отправлять не нужно.")

            return filtered_users
        except Exception as e:
            logging.error(f"Ошибка при получении пользователей: {e}")
            return []

    async def filter_users_with_servers(self, batch: List[int]) -> List[int]:
        """
        Фильтрует пользователей с серверами и проверяет их подписку.
        """
        unsubscribed_users = []

        async def check_user(chat_id: int):
            try:
                # Загружаем пользователя
                user = await UserCl.load_user(chat_id)
                if not user or not user.servers:
                    print(f"Пользователь {chat_id} не имеет серверов. Пропускаем.")
                    return None

                # Проверяем подписку
                if await user.is_subscribed_on_channel.get():
                    print(f"Пользователь {chat_id} подписан. Статус обновлен в базе.")
                    return None
                else:
                    print(f"Пользователь {chat_id} не подписан. Добавляем в список.")
                    return chat_id
            except Exception as e:
                print(f"Ошибка при обработке пользователя {chat_id}: {e}")
                return None

        # Асинхронная проверка всех пользователей в батче
        results = await asyncio.gather(*(check_user(chat_id) for chat_id in batch))

        # Фильтруем только неподписанных
        unsubscribed_users = [chat_id for chat_id in results if chat_id is not None]
        return unsubscribed_users

    def get_message_template(self) -> str:
        """
        Текст уведомления для отписавшихся пользователей.
        """
        return (
            f"📢 <b>Уважаемый пользователь!</b>\n\n"
            f"🐧 Пожалуйста, подпишитесь на наш канал <a href='https://t.me/{self.channel_username}'>@Ping_hub</a>,\n"
            "чтобы продолжить пользоваться VPN.\n\n"
            "Это поможет нам поддерживать сервис\n"
            "и радовать вас новыми функциями. 🚀"
        )

    def get_keyboard(self) -> InlineKeyboardMarkup:
        """
        Возвращает клавиатуру с кнопками для подписки.
        """
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📢 Перейти на канал", url=f"https://t.me/{self.channel_username}")],
                [InlineKeyboardButton(text="✅ Я подписался", callback_data="i_am_subscribed")]
            ]
        )
        return keyboard

    async def after_send_success(self, user_id: int):
        """
        Обновление поля notification_data в таблице после успешной отправки уведомления.
        Теперь используется уникальное значение типа уведомления: unsubscribed_notification_мм_дд.
        """
        # Генерируем уникальный тип уведомления
        today = datetime.now().strftime("%m_%d")  # Формат мм_дд
        notification_type = f"unsubscribed_notification_{today}"

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
