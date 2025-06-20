import asyncio
import json
import os

from redis.exceptions import RedisError
import logging

from bot.handlers.admin import send_admin_log
from bot_instance import bot
from models.country_server_data import get_name_server_by_ip
from redis_configs.redis_settings import redis_client_main
from work_user_api.XUIApiClient import XUIApiClient
from work_user_api.decryptor import get_server_credentials_by_ip
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)



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

class ReadyWorkApiServer():
    def __init__(self, server_ip: str):
        try:
            all_data = get_server_credentials_by_ip(server_ip)
        except ValueError as e:
            my_logging.error(f"Ошибка: {e}")
            import asyncio
            loop = asyncio.get_event_loop()
            loop.create_task(send_admin_log(bot, f"result_check_enable: Ошибка при поиске шифрованных данных по серверу {server_ip}"))
            raise  # <-- ВАЖНО! Прерываем выполнение, чтобы не продолжать без данных

        # Инициализируем XUIApiClient с нужными данными
        self.server = XUIApiClient(
            host=all_data["xui_url"],
            username=all_data["login"],
            password=all_data["password"]
        )
        self.server_ip = server_ip



    async def process_change_enable_user(self, email_key: str, enable: bool, chat_id: int, uuid_value: str):
        try:
            await self.server.login()
            success, response = await self.server.toggle_user_enable_by_email(email=email_key, enable=enable)
            # После изменения — проверяем реальное состояние
            actual_enable = await self.server.check_enable(email_key)
            name_server = await get_name_server_by_ip(self.server_ip)
            if not success:
                status_value = "error"
            else:
                status_value = "success"



            my_logging.info(f"API VLESS изменение enable и проверка статуса: {actual_enable}")


            # Отправляем результат в Redis
            redis_payload = {
                "status": status_value,
                "task_type": "result_change_enable_user",
                "enable": actual_enable,
                "user_ip": None,  # если IP нет, оставляем пустым
                "uuid_value": uuid_value,
                "protocol": "vless",
                "chat_id": chat_id,
                "server_ip": self.server_ip,
                "name_server": name_server
            }
            await redis_client_main.lpush(NAME_RESULT_QUEUE, json.dumps(redis_payload))
            my_logging.info(f"Обновленные данные отправлены в Redis: {redis_payload}")
            return True if status_value == "success" else False
        except RedisError as e:
            my_logging.error(f"Ошибка подключения к Redis: {e}. Повторная попытка через 5 секунд...")
            await asyncio.sleep(5)
            return False
        except Exception as e:
            my_logging.error(f"Ошибка при изменении пользователя через API: {e}")
            return False

    async def close(self):
        await self.server.close()
