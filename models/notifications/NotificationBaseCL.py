import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional
from bot.handlers.admin import ADMIN_CHAT_IDS, send_admin_log


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
                if user_id in ADMIN_CHAT_IDS:
                    await self.after_send_success(user_id)
                    # Отправляем сообщение
                    await bot.send_message(
                        chat_id=user_id,
                        text=message_template,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                    self.success_count += 1  # Увеличиваем счетчик успешных отправок
                      # Обработка после успешной отправки

            except Exception as e:
                self.error_count += 1  # Увеличиваем счетчик ошибок
                await self.handle_send_error(user_id, e)  # Обработка ошибок отправки

        # Параллельная отправка сообщений пользователям в батче
        await asyncio.gather(*[send_message(user_id) for user_id in batch])




    async def handle_send_error(self, user_id: int, error: Exception):
        """
        Обработка ошибок отправки уведомления.
        Можно переопределить в дочерних классах для логирования ошибок.
        """
        print(f"Ошибка при отправке уведомления пользователю {user_id}: {error}")

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

        # После завершения отправки всех уведомлений отправляем результат администратору
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
