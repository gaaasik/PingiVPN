import asyncio
import logging
import os
from abc import ABC, abstractmethod
from typing import List, Optional

import aiosqlite

from bot.handlers.admin import ADMIN_CHAT_IDS, send_admin_log


async def handle_send_error(user_id: int, error: Exception):
    """
    Обработка ошибок отправки уведомления.
    Если бот был заблокирован пользователем — обновляем поле active_chat = FALSE.
    """
    error_text = str(error).lower()
    print(f"Ошибка при отправке пользователю {user_id}: {error_text}")

    try:
        async with aiosqlite.connect(os.getenv("database_path_local")) as db:
            await db.execute(
                "UPDATE users SET active_chat = 0 WHERE chat_id = ?",
                (user_id,)
            )
            await db.commit()
        logging.info(f"❌ Пользователь {user_id} заблокировал бота. active_chat = FALSE")
    except Exception as db_error:
        logging.error(f"Ошибка при обновлении active_chat для {user_id}: {db_error}")


class NotificationBase(ABC):
    def __init__(self, batch_size: int = 50):
        self.batch_size = batch_size
        self.target_users = []
        self.success_count = 0  # Счетчик успешных отправок
        self.error_count = 0  # Счетчик ошибок отправки

    @abstractmethod
    async def fetch_target_users(self) -> List[int]:
        """Получение пользователей для уведомления"""
        pass

    @abstractmethod
    def get_message_template(self) -> str:
        """Получение текста уведомления"""
        pass

    @abstractmethod
    def get_keyboard(self) -> Optional[object]:
        """Получение клавиатуры для уведомления"""
        pass

    @abstractmethod
    def after_send_success(self, user_id: int):
        """
        Действия после успешной отправки уведомления пользователю.
        Может быть переопределено в дочерних классах.
        """
        pass

    def split_into_batches(self, users: List[int]) -> List[List[int]]:
        """
        Делит список пользователей на батчи заданного размера.
        """
        for i in range(0, len(users), self.batch_size):
            yield users[i:i + self.batch_size]

    async def send_batch(self, bot, batch: List[int]):
        """
        Отправка уведомлений батчами.
        Реальная асинхронная отправка сообщений нескольким пользователям одновременно.
        """
        message_template = self.get_message_template()
        keyboard = self.get_keyboard()

        async def send_message(user_id):
            """Асинхронная функция для отправки сообщения одному пользователю."""
            try:
                # Проверка active_chat из базы
                async with aiosqlite.connect(os.getenv("database_path_local")) as db:
                    query = "SELECT active_chat FROM users WHERE chat_id = ?"
                    async with db.execute(query, (user_id,)) as cursor:
                        row = await cursor.fetchone()

                    if not row or row[0] != 1:
                        return  # Не отправляем сообщение

                await bot.send_message(
                    chat_id=user_id,
                    text=message_template,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
                self.success_count += 1  # Увеличиваем счетчик успешных отправок
                  # Обработка после успешной отправки
                await self.after_send_success(user_id)

            # #Для тестов отправлено сообщение
            #     if user_id in ADMIN_CHAT_IDS:
            #         await bot.send_message(
            #             chat_id=user_id,
            #             text=message_template,
            #             reply_markup=keyboard,
            #             parse_mode="HTML"
            #         )
            #     else:
            #         logging.info(f"Пользователю {user_id} отправлено сообщение.")
            #
            #     self.success_count += 1  # Увеличиваем счетчик успешных отправок
            #       # Обработка после успешной отправки
            #     await self.after_send_success(user_id)

            except Exception as e:
                self.error_count += 1  # Увеличиваем счетчик ошибок
                await handle_send_error(user_id, e)  # Обработка ошибок отправки

        # Параллельная отправка сообщений пользователям в батче
        await asyncio.gather(*[send_message(user_id) for user_id in batch])

    async def run(self, bot):
        """
        Запуск уведомления
        """
        # Сбрасываем счётчики перед выполнением
        self.success_count = 0
        self.error_count = 0
        self.target_users = await self.fetch_target_users()

        # Разделяем пользователей на батчи и отправляем уведомления
        for batch in self.split_into_batches(self.target_users):
            await self.send_batch(bot, batch)

        # После завершения отправки всех уведомлений отправляем результат администратору active_chat
        if self.target_users:  # Проверяем, есть ли пользователи в выборке
            summary_message = (
                f"📊 *Уведомления завершены:*\n\n"
                f"✅ Успешно отправлено: {self.success_count}.\n"
                f"❌ Не удалось отправить: {self.error_count}."
            )
            try:
                await send_admin_log(bot, summary_message)
            except Exception as e:
                print(f"Ошибка при отправке сводного отчета: {e}")
        else:
            print("Нет пользователей для уведомления. Отправка сводки отменена.")
