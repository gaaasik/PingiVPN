import logging
from .base_processor import BaseResultProcessor
from models.UserCl import UserCl

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class ResultCreateUsers(BaseResultProcessor):
    """Обработчик результата создания пользователей VLESS."""

    async def process(self, task_data: dict):
        """
        Обрабатывает результат создания пользователей.
        """
        logging.info(f"📥 Получен результат создания пользователей: {task_data}")

        status = task_data.get("status", "error")
        chat_id = task_data.get("chat_id", None)
        count_users = task_data.get("count_users", 0)
        all_urls = task_data.get("all_urls", [])

        if status == "success":
            message = f"✅ Успешно создано {count_users} пользователей.\n\n🔗 Ссылки на VLESS:\n" + "\n".join(all_urls)
            logging.info(f"📌 Созданные пользователи: {count_users}")
        else:
            message = f"❌ Ошибка при создании пользователей!\n\n{task_data.get('message', 'Неизвестная ошибка')}"
            logging.error("❌ Ошибка при обработке result_create_users")

        # 🚀 Отправляем сообщение в Telegram или логируем (зависит от проекта)
        if chat_id:
            await self.send_message_to_user(chat_id, message)

        logging.info(f"📨 Сообщение отправлено в Telegram: {message}")

