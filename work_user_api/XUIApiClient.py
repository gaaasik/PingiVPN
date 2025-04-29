import asyncio
import json
import logging
import requests

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
class XUIApiClient:
    def __init__(self, host: str, username: str, password: str):
        self.host = host.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = False
        self.authenticated = False

    async def login(self) -> bool:
        data = {"username": self.username, "password": self.password}
        try:
            my_logging.info(f"Пытаемся авторизоваться в x-ui API: {self.host}")
            response = await asyncio.to_thread(self.session.post, f"{self.host}/login", data=data, verify=False, timeout=5)
            self.authenticated = response.status_code == 200
            if self.authenticated:
                my_logging.info("Успешная авторизация в x-ui API")
            else:
                my_logging.warning(
                    f" Ошибка авторизации в x-ui API. Код: {response.status_code}, Текст: {response.text}")
            return self.authenticated
        except Exception as e:
            my_logging.error(f"Исключение при авторизации в x-ui API: {e}")
            return False

    async def list_clients(self):
        try:
            response = await asyncio.to_thread(self.session.get,f"{self.host}/panel/api/inbounds/list", verify=False, timeout=5)
            return response.json()
        except Exception as e:
            my_logging.error(f"Ошибка при получении списка клиентов: {e}")
            return {}

    async def find_client_by_email(self, email: str):
        client_list = await self.list_clients()
        for inbound in client_list.get("obj", []):
            settings = json.loads(inbound.get("settings", "{}"))
            for client in settings.get("clients", []):
                if client.get("email") == email:
                    return inbound["id"], client
        return None, None

    async def update_client_enable_status(self, inbound_id: int, client_id: str, email: str, enable: bool, sub_id: str):

        headers = {"Accept": "application/json"}
        settings = {
            "clients": [{
                "email": email,
                "enable": enable,
                "expiryTime": 0,
                "flow": "xtls-rprx-vision",
                "id": client_id,
                "limitIp": 0,
                "reset": 0,
                "subId": sub_id,
                "tgId": "",
                "totalGB": 0
            }]
        }

        data = {
            "id": inbound_id,
            "settings": json.dumps(settings)
        }
        url = f"{self.host}/panel/api/inbounds/updateClient/{client_id}"
        response = await asyncio.to_thread(self.session.post, url, headers=headers, json=data, timeout=5)

        return response.status_code == 200, response.json()

    async def toggle_user_enable_by_email(self, email: str, enable: bool):
        if not self.authenticated:
            if not await self.login():
                return False, {"error": "Authentication failed"}

        inbound_id, client = await self.find_client_by_email(email)
        if not inbound_id or not client:
            return False, {"error": f"Client with email {email} not found"}

        client_id = client["id"]
        sub_id = client.get("subId", "")  # забираем subId из клиента, если нет — ставим пустую строку
        return await self.update_client_enable_status(inbound_id, client_id, email, enable, sub_id)


    async def check_enable(self, email: str) -> bool | None:
        """
        Проверяет текущее значение enable для клиента по email.
        Возвращает True / False или None если клиент не найден.
        """
        if not self.authenticated:
            if not self.login():
                return None

        inbound_id, client = await self.find_client_by_email(email)
        if client:
            return client.get("enable")
        else:
            return None