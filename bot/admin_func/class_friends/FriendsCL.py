import os
import aiosqlite
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv
import logging

from models.UserCl import UserCl

load_dotenv()

DATABASE_PATH = os.getenv("database_path_local")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

class FriendsManager:
    """
    Класс для управления списком друзей.
    """

    @staticmethod
    async def add_friend(admin_chat_id: int, friend_chat_id: int, friend_username: Optional[str] = None) -> bool:
        """
        Добавляет друга и продлевает подписку так, чтобы у него было 365 дней.
        """
        now = datetime.now()
        try:
            async with aiosqlite.connect(DATABASE_PATH) as db:
                # Проверяем, есть ли друг уже в списке
                async with db.execute(
                        "SELECT id FROM friends WHERE friend_chat_id = ? AND status = 'active'",
                        (friend_chat_id,),
                ) as cursor:
                    if await cursor.fetchone():
                        logging.warning(
                            f"❌ Пользователь {friend_chat_id} уже добавлен в список друзей админа {admin_chat_id}."
                        )
                        return False  # Уже друг

                # Добавляем друга с указанием admin_chat_id
                await db.execute(
                    """
                    INSERT INTO friends (admin_chat_id, friend_chat_id, friend_username, date_added, status)
                    VALUES (?, ?, ?, ?, 'active')
                    """,
                    (admin_chat_id, friend_chat_id, friend_username, now.strftime("%d.%m.%Y %H:%M:%S")),
                )

                await db.commit()  # Закрываем транзакцию перед продлением подписки
                logging.info(f"✅ Пользователь {friend_chat_id} добавлен в список друзей админа {admin_chat_id}.")

            # Вызываем продление подписки вне блока `async with`
            await FriendsManager._extend_subscription(friend_chat_id, 365)

            return True

        except Exception as e:
            logging.error(f"⚠️ Ошибка при добавлении друга {friend_chat_id} администратором {admin_chat_id}: {e}")
            return False

    @staticmethod
    async def is_friend(friend_chat_id: int) -> bool:
        """
        Проверяет, является ли пользователь другом.
        """
        try:
            async with aiosqlite.connect(DATABASE_PATH) as db:
                async with db.execute(
                    "SELECT id FROM friends WHERE friend_chat_id = ? AND status = 'active'",
                    (friend_chat_id,),
                ) as cursor:
                    is_friend = await cursor.fetchone() is not None

            logging.info(f"🔍 Проверка друга {friend_chat_id}: {'Да' if is_friend else 'Нет'}")
            return is_friend

        except Exception as e:
            logging.error(f"⚠️ Ошибка при проверке друга {friend_chat_id}: {e}")
            return False

    @staticmethod
    async def remove_friend(friend_chat_id: int) -> bool:
        """
        Удаляет друга (меняет статус на 'removed') и обрезает подписку до 7 дней.
        """
        try:
            async with aiosqlite.connect(DATABASE_PATH) as db:
                await db.execute(
                    "UPDATE friends SET status = 'removed' WHERE friend_chat_id = ?", (friend_chat_id,)
                )

                # Устанавливаем подписку на 7 дней
                await FriendsManager._extend_subscription(friend_chat_id, 7)

                await db.commit()
                logging.info(f"❌ Пользователь {friend_chat_id} удален из списка друзей.")
                return True

        except Exception as e:
            logging.error(f"⚠️ Ошибка при удалении друга {friend_chat_id}: {e}")
            return False

    @staticmethod
    async def _extend_subscription(chat_id: int, target_days: int):
        """
        Динамически продлевает подписку до нужного количества дней, используя класс ServerCl.
        """
        now = datetime.now()

        try:
            # Загружаем пользователя
            user = await UserCl.load_user(chat_id)
            if not user or not user.active_server:
                logging.warning(f"❌ Пользователь {chat_id} не найден или не имеет активного сервера.")
                return

            # Получаем текущую дату окончания подписки
            current_end_date_str = await user.active_server.date_key_off.get()

            try:
                current_end_date = datetime.strptime(current_end_date_str, "%d.%m.%Y %H:%M:%S")
            except ValueError:
                logging.warning(f"⚠️ Некорректная дата у {chat_id}, устанавливаем с текущего момента.")
                current_end_date = now

            # Вычисляем, сколько дней нужно добавить
            days_left = (current_end_date - now).days
            days_to_add = max(target_days - days_left, 0)
            new_end_date = current_end_date + timedelta(days=days_to_add)

            # Устанавливаем новую дату подписки через `ServerCl`
            await user.active_server.date_key_off.set(new_end_date.strftime("%d.%m.%Y %H:%M:%S"))

            logging.info(
                f"🔄 Подписка {chat_id} продлена до {new_end_date.strftime('%d.%m.%Y %H:%M:%S')} "
                f"(добавлено {days_to_add} дней)"
            )

        except Exception as e:
            logging.error(f"⚠️ Ошибка при продлении подписки {chat_id}: {e}")

