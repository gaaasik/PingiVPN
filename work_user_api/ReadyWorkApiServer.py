import logging
from typing import Dict
from work_user_api.XUIApiClient import XUIApiClient
from work_user_api.decryptor import get_server_credentials_by_ip

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("payments.log"),
        logging.StreamHandler()
    ],
    encoding="utf-8"
)
my_logging = logging.getLogger(__name__)


class ReadyWorkApiServer():
    def __init__(self, server_ip: str):
        try:
            all_data = get_server_credentials_by_ip(server_ip)
        except ValueError as e:
            my_logging.error(f"Ошибка: {e}")

        # Инициализируем XUIApiClient с нужными данными
        self.server = XUIApiClient(
            host=all_data["xui_url"],
            username=all_data["login"],
            password=all_data["password"]
        )
        self.server.login()

    async def process_change_enable_user(self, email_key: str, enable: bool, chat_id: int):

        try:
            success, response = self.server.toggle_user_enable_by_email(email=email_key, enable=enable)

            result = {
                "status": "success" if success else "error",
                "task_type": "result_change_enable_user",
                "chat_id": chat_id,
                "protocol": "vless",
                "enable": enable,
                "email_key": email_key,
                "response": response
            }

            my_logging.info(f"API VLESS изменение enable: {result}")
            actual_enable = self.server.check_enable(email_key)

        except Exception as e:
            my_logging.error(f"Ошибка при изменении пользователя через API: {e}")


