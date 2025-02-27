import os
import json
import logging
import redis.asyncio as redis
from typing import List
from models.country_server_data import get_name_server_by_ip
from models.UserCl import UserCl  # Импортируем UserCl для получения списка пользователей

# ТЕСТОВЫЙ IP-адресов серверов
# SERVERS_IP_FOR_CHECK_ENABLE = [
#     "194.87.208.18",
#     "147.45.242.155",
# ]

#Список IP - адресов серверов
SERVERS_IP_FOR_CHECK_ENABLE = [
    "194.164.216.197",  # Server_25000
    "80.209.243.248",  # USA_27000
    "195.26.231.178",  # Germany_28000
    "66.248.207.185",  # NL_29000
    "195.26.230.208",  # FIN_31000
    "176.222.53.29",  # NL_32000
    "5.39.220.237",  # NL_33000
]

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("tasks.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class TaskRedis:
    """Класс для управления отправкой задач в Redis."""

    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("ip_redis_server"),
            port=int(os.getenv("port_redis")),
            password=os.getenv("password_redis"),
            decode_responses=True,
        )

    async def send_check_enable_task(self, server_ip: str, users: List[UserCl]):
        """
        Отправляет задачу 'check_enable_user' в очередь Redis для указанного сервера.

        :param server_ip: IP-адрес сервера.
        :param users: Список объектов UserCl, привязанных к серверу.
        """
        try:
            server_name = await get_name_server_by_ip(server_ip)  # Получаем имя сервера
            queue_name = f"queue_task_{server_name}"  # Формируем имя очереди в Redis

            for us in users:
                task_data = {
                    "task_type": "check_enable_user",
                    "name_protocol": await us.active_server.name_protocol.get(),
                    "chat_id": us.chat_id,
                    "user_ip": await us.active_server.user_ip.get(),
                    "uuid_value": await us.active_server.uuid_id.get(),
                    "enable": await us.active_server.enable.get(),
                }

                await self.redis_client.rpush(queue_name, json.dumps(task_data))  # Отправка задачи в очередь
                logger.info(f"Отправлена задача: {task_data} -> Очередь: {queue_name}")

        except Exception as e:
            logger.error(f"Ошибка при отправке задачи на сервер {server_ip}: {e}")

    async def close(self):
        """Закрывает соединение с Redis."""
        await self.redis_client.close()

    async def send_creating_user(self, chat_id):
        """
        Отправляет задачу 'creating_user' в очередь Redis для указанного сервера.

        :param server_ip: IP-адрес сервера.
        :param users: Список объектов UserCl, привязанных к серверу.
        """
        try:
            us = await UserCl.load_user(chat_id)
            server_ip = await us.active_server.server_ip.get()
            server_name = await get_name_server_by_ip(server_ip)  # Получаем имя сервера
            queue_name = f"queue_task_{server_name}"  # Формируем имя очереди в Redis

            task_data = {
                "task_type": "creating_user",
                "name_protocol": await us.active_server.name_protocol.get(),
                "chat_id": chat_id,
                "user_ip": await us.active_server.user_ip.get(),
                "uuid_value": await us.active_server.uuid_id.get(),
                "enable": await us.active_server.enable.get(),
                "count_users": 1,
            }

            await self.redis_client.rpush(queue_name, json.dumps(task_data))  # Отправка задачи в очередь
            logger.info(f"Отправлена задача: {task_data} -> Очередь: {queue_name}")

        except Exception as e:
            logger.error(f"Ошибка при отправке задачи на сервер {server_ip}: {e}")





async def send_check_tasks_for_servers():
    """
    Запускает отправку задач 'check_enable_user' для всех серверов в списке `SERVERS_IP`.
    """
    task_manager = TaskRedis()
    users_to_check = {}  # Словарь {server_ip: [список пользователей]}

    chat_ids = await UserCl.get_all_users()  # Получаем всех пользователей

    for chat_id in chat_ids:
        us = await UserCl.load_user(chat_id)

        if us and await us.count_key.get() > 0:  # Проверяем, есть ли у пользователя серверы
            active_server_ip = await us.active_server.server_ip.get()

            if active_server_ip in SERVERS_IP_FOR_CHECK_ENABLE:  # Проверяем, находится ли сервер в списке
                if active_server_ip not in users_to_check:
                    users_to_check[active_server_ip] = []
                users_to_check[active_server_ip].append(us)

    # Отправляем задачи в Redis для каждого сервера
    for server_ip, users in users_to_check.items():
        await task_manager.send_check_enable_task(server_ip, users)

    await task_manager.close()  # Закрываем соединение с Redis


