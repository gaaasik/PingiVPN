import datetime
import json
from typing import Dict

import requests

from logging_config.my_logging import my_logging
from task_processor.protocols.base_class import VPNProcessor
from task_processor.server_settings import ServerSettings


class XUIApiClient:
    def __init__(self, host: str, username: str, password: str):
        self.host = host.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.authenticated = False

    def login(self) -> bool:
        data = {"username": self.username, "password": self.password}
        response = self.session.post(f"{self.host}/login", data=data)
        self.authenticated = response.status_code == 200
        return self.authenticated

    def list_clients(self):
        if not self.authenticated:
            self.login()
        response = self.session.get(f"{self.host}/panel/api/inbounds/list")
        return response.json()

    def find_client_by_email(self, email: str):
        client_list = self.list_clients()
        for inbound in client_list.get("obj", []):
            settings = json.loads(inbound.get("settings", "{}"))
            for client in settings.get("clients", []):
                if client.get("email") == email:
                    return inbound["id"], client
        return None, None

    def update_client_enable_status(self, inbound_id: int, client_id: str, email: str, enable: bool, days: int = 30):
        expiry_time = int((datetime.datetime.utcnow().timestamp() + (days * 86400)) * 1000)
        headers = {"Accept": "application/json"}
        settings = {
            "clients": [{
                "id": client_id,
                "alterId": 90,
                "email": email,
                "limitIp": 3,
                "totalGB": 0,
                "expiryTime": expiry_time,
                "enable": enable,
                "tgId": email,
                "subId": ""
            }]
        }
        data = {
            "id": inbound_id,
            "settings": json.dumps(settings)
        }
        url = f"{self.host}/panel/api/inbounds/updateClient/{client_id}"
        response = self.session.post(url, headers=headers, json=data)
        return response.status_code == 200, response.json()

    def toggle_user_enable_by_email(self, email: str, enable: bool, days: int = 30):
        if not self.authenticated:
            if not self.login():
                return False, {"error": "Authentication failed"}

        inbound_id, client = self.find_client_by_email(email)
        if not inbound_id or not client:
            return False, {"error": f"Client with email {email} not found"}

        client_id = client["id"]
        return self.update_client_enable_status(inbound_id, client_id, email, enable, days)


class VlessApiProcessor(VPNProcessor):
    def __init__(self):
        self.client = XUIApiClient(
            host=ServerSettings.XUI_HOST,
            username=ServerSettings.XUI_LOGIN,
            password=ServerSettings.XUI_PASSWORD
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
            my_logging.error(f"❌ Ошибка при изменении пользователя через API: {e}")

    async def get_user_traffic(self, user_identifier: str) -> Dict:
        return {"transfer_received": "0", "transfer_sent": "0"}  # заглушка

    async def get_user_enable_status(self, user_identifier: str) -> bool:
        try:
            _, client = self.client.find_client_by_email(user_identifier)
            return client.get("enable", False)
        except Exception as e:
            my_logging.error(f"❌ Ошибка при проверке статуса пользователя через API: {e}")
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
