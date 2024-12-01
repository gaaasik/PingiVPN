from .NotificationBaseCL import NotificationBase
from typing import List

class PaymentReminder(NotificationBase):
    def __init__(self, batch_size: int = 50):
        super().__init__(batch_size)

    async def fetch_target_users(self) -> List[int]:
        """
        Получение пользователей с неоплаченными счетами.
        """
        query = "SELECT chat_id FROM users WHERE has_pending_payment = 1"
        # Здесь будет логика для выполнения SQL-запроса
        return await self._mock_fetch_users()

    async def _mock_fetch_users(self) -> List[int]:
        """
        Мок данных для тестирования.
        """
        return [11111111, 22222222, 33333333]

    def get_message_template(self) -> str:
        """
        Шаблон сообщения для напоминания об оплате.
        """
        return (
            "💳 У вас есть неоплаченный счет. "
            "Пожалуйста, завершите оплату, чтобы продолжить использование наших услуг."
        )

    async def after_send_success(self, user_id: int):
        """
        Обновление статуса пользователя после успешной отправки уведомления.
        """
        query = "UPDATE users SET notified_about_payment = 1 WHERE chat_id = ?"
        # Здесь добавляем логику обновления базы данных
        pass
