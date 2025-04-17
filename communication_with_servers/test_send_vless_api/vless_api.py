import json
import logging
from typing import Dict

from communication_with_servers.test_send_vless_api.XUIApiClient import XUIApiClient
from communication_with_servers.test_send_vless_api.base_class import VPNProcessor
from communication_with_servers.test_send_vless_api.server_settings import ServerSettings


# Настройка логирования
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

class VlessApiProcessor(VPNProcessor):
    def __init__(self):
        self.client = XUIApiClient(
            host="https://194.164.216.151:14928/F9qWQiN4I5yQ9q6/",
            username="96Rq2jrSiw",
            password="imEdOV0VrJ"
        )
        self.client.login()

    async def process_change_enable_user(self, task_data: Dict):
        email_key = task_data["email_key"]
        enable = task_data["enable"]
        chat_id = task_data["chat_id"]

        try:
            success, response = self.client.toggle_user_enable_by_email(email=email_key, enable=enable)

            result = {
                "status": "success" if success else "error",
                "task_type": "result_change_enable_user",
                "chat_id": chat_id,
                "protocol": "vless",
                "enable": enable,
                "email_key": email_key,
                "response": response
            }

            redis_client = await ServerSettings.get_redis_client()
            await redis_client.lpush(ServerSettings.NAME_RESULT_QUEUE, json.dumps(result))

            my_logging.info(f"API VLESS изменение enable: {result}")
        except Exception as e:
            my_logging.error(f"Ошибка при изменении пользователя через API: {e}")

    async def get_user_traffic(self, user_identifier: str) -> Dict:
        return {"transfer_received": "0", "transfer_sent": "0"}  # заглушка

    async def get_user_enable_status(self, user_identifier: str) -> bool:
        try:
            _, client = self.client.find_client_by_email(user_identifier)
            return client.get("enable", False)
        except Exception as e:
            my_logging.error(f"Ошибка при проверке статуса пользователя через API: {e}")
            return False

    async def process_delete_user(self, task_data: Dict):
        my_logging.warning("Удаление пользователя через API ещё не реализовано.")

    async def creating_user(self, task_data: Dict, count_users: int):
        my_logging.warning("Создание пользователя через API пока не реализовано.")

    async def get_count_true_user(self) -> int:
        try:
            client_list = self.client.list_clients()
            count = 0
            for inbound in client_list.get("obj", []):
                settings = json.loads(inbound.get("settings", "{}"))
                clients = settings.get("clients", [])
                count += sum(1 for c in clients if c.get("enable") is True)
            return count
        except Exception as e:
            my_logging.error(f"Ошибка при подсчёте активных пользователей через API: {e}")
            return 0
