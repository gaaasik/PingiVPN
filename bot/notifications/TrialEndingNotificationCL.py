from .NotificationBaseCL import NotificationBase
from typing import List

class TrialEndingNotification(NotificationBase):
    def __init__(self, batch_size: int = 50):
        super().__init__(batch_size)

    async def fetch_target_users(self) -> List[int]:
        """
        Получение пользователей, чей пробный период заканчивается завтра.
        """
        query = (
            "SELECT chat_id FROM users WHERE trial_end_date = CURRENT_DATE + 1"
        )
        # Здесь будет логика для выполнения SQL-запроса
        return await self._mock_fetch_users()

    async def _mock_fetch_users(self) -> List[int]:
        """
        Мок данных для тестирования.
        """
        return [44444444, 55555555, 66666666]

    def get_message_template(self) -> str:
        """
        Шаблон сообщения для уведомления о завершении пробного периода.
        """
        return (
            "⏳ Ваш пробный период заканчивается завтра. "
            "Подпишитесь, чтобы продолжить использовать наш сервис!"
        )

    async def after_send_success(self, user_id: int):
        """
        Обновление статуса пользователя после успешной отправки уведомления.
        """
        query = "UPDATE users SET notified_about_trial_ending = 1 WHERE chat_id = ?"
        # Здесь добавляем логику обновления базы данных
        pass
