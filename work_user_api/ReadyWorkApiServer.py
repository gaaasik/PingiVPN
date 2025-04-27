import asyncio
import json
import os

from redis.exceptions import RedisError
import logging

from bot.handlers.admin import send_admin_log
from bot_instance import bot
from redis_configs.redis_settings import redis_client_main
from work_user_api.XUIApiClient import XUIApiClient
from work_user_api.decryptor import get_server_credentials_by_ip
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def ensure_logged_in(func):
    async def wrapper(self, *args, **kwargs):
        if not self.server.authenticated:
            await self.server.login()
        return await func(self, *args, **kwargs)
    return wrapper

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
NAME_RESULT_QUEUE = os.getenv("name_queue_result_task").strip()


class ReadyWorkApiServer:
    def __init__(self, server_ip: str):
        """
        Инициализация подключения к серверу по IP.
        Загружаем xui_url, login, password и токен.
        """
        all_data = get_server_credentials_by_ip(server_ip)
        full_url = all_data.get("xui_url")

        if not full_url:
            raise ValueError(f"Нет xui_url для сервера {server_ip}")

        # Извлекаем базовый адрес и токен
        parts = full_url.split("/", 3)
        if len(parts) < 4:
            raise ValueError(f"Неверный формат xui_url для сервера {server_ip}")

        self.base_url = parts[0] + '//' + parts[2]  # https://ip:port
        self.token = parts[3]  # сам токен

        self.server = XUIApiClient(base_url=self.base_url, token=self.token)

    @ensure_logged_in
    async def process_change_enable_user(self, email_key: str, enable: bool, chat_id: int, uuid_value: str) -> None:
        """
        Процесс изменения активности пользователя по email.
        """
        try:
            await self.server.login()
            success, _ = await self.server.toggle_user_enable_by_email(email=email_key, enable=enable)

            if not success:
                my_logging.error(f"Ошибка при изменении состояния пользователя {email_key} через API.")
        except Exception as e:
            my_logging.error(f"Ошибка при изменении пользователя через API: {e}")

    @ensure_logged_in
    async def process_get_clients(self) -> dict:
        """
        Получить список всех клиентов.
        """
        try:
            await self.server.login()
            return await self.server.list_clients()
        except Exception as e:
            my_logging.error(f"Ошибка при получении списка клиентов: {e}")
            return {"error": str(e)}

