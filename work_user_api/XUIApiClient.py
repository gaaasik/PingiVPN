import aiohttp
import asyncio
import json
import logging

logging.basicConfig(level=logging.INFO)
my_logging = logging.getLogger(__name__)

class XUIApiClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.authenticated = False

    async def login(self) -> bool:
        # Авторизация через токен считается успешной сразу
        self.authenticated = True
        return True

    def _full_url(self, path: str) -> str:
        """Формирование полного URL с токеном в пути."""
        return f"{self.base_url}/{self.token}{path}"

    async def list_clients(self) -> dict:
        """Запрос списка клиентов."""
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    self._full_url("/panel/api/inbounds/list"),
                    ssl=False
                ) as response:
                    if response.content_type != "application/json":
                        my_logging.error(f"Сервер вернул неправильный тип ответа: {response.content_type}")
                        text = await response.text()
                        my_logging.error(f"Ответ сервера: {text}")
                        return {}
                    return await response.json()
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
        headers = self._auth_headers()
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
        url = f"{self.base_url}/panel/api/inbounds/updateClient/{client_id}"
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, headers=headers, json=data, ssl=False) as response:
                    return response.status == 200, await response.json()
        except Exception as e:
            my_logging.error(f"Ошибка при обновлении клиента: {e}")
            return False, {}

    async def toggle_user_enable_by_email(self, email: str, enable: bool):
        if not self.authenticated:
            await self.login()

        inbound_id, client = await self.find_client_by_email(email)
        if not inbound_id or not client:
            return False, {"error": "Client not found"}

        client_id = client["id"]
        sub_id = client.get("subId", "")
        return await self.update_client_enable_status(inbound_id, client_id, email, enable, sub_id)

    async def check_enable(self, email: str) -> bool | None:
        if not self.authenticated:
            await self.login()

        inbound_id, client = await self.find_client_by_email(email)
        if client:
            return client.get("enable")
        return None