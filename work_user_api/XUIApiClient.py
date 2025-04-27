import aiohttp
import asyncio
import json
import logging

my_logging = logging.getLogger(__name__)

class XUIApiClient:
    def __init__(self, host: str, username: str, password: str):
        self.host = host.rstrip('/')
        self.username = username
        self.password = password
        self.session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True))
        self.authenticated = False

    async def login(self) -> bool:
        data = {
            "username": self.username,
            "password": self.password
        }
        try:
            my_logging.info(f"Пытаемся авторизоваться в x-ui API: {self.host}")
            async with self.session.post(f"{self.host}/login", data=data, ssl=False) as response:
                if response.status == 200:
                    self.authenticated = True
                    my_logging.info("Успешная авторизация в x-ui API")
                else:
                    text = await response.text()
                    my_logging.warning(f"Ошибка авторизации в x-ui API. Код: {response.status}, Текст: {text}")
                    self.authenticated = False
                return self.authenticated
        except Exception as e:
            my_logging.error(f"Исключение при авторизации в x-ui API: {e}")
            return False

    async def list_clients(self) -> dict:
        if not self.authenticated:
            await self.login()
        try:
            async with self.session.get(f"{self.host}/panel/api/inbounds/list", ssl=False) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    my_logging.error(f"Ошибка при получении списка клиентов: {response.status}, текст: {text}")
                    return {}
        except Exception as e:
            my_logging.error(f"Ошибка при получении списка клиентов: {e}")
            return {}

    async def close(self):
        await self.session.close()
