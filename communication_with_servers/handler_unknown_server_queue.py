import os
import json
import logging
import redis.asyncio as redis

from models.UserCl import UserCl
from models.country_server_data import get_json_country_server_data


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("payments.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)



async def process_unknown_server_queue():
    """Обрабатывает очередь `queue_task_Unknown_Server` и перемещает задачи с известными именами серверов."""
    try:
        logging.info(f"Запустился процесс обработки очереди queue_task_Unknown_Server")
        # Подключение к Redis
        redis_client = redis.Redis(
            host=os.getenv('ip_redis_server'),
            port=int(os.getenv('port_redis')),
            password=os.getenv('password_redis'),
            decode_responses=True
        )

        # Загрузка данных о серверах
        server_data = await get_json_country_server_data()
        if server_data is None:
            raise RuntimeError("Не удалось загрузить данные о серверах.")

        # Получение всех задач из очереди `queue_task_Unknown_Server`
        queue_name = "queue_task_Unknown_Server"
        tasks = await redis_client.lrange(queue_name, 0, -1)

        for task_json in tasks:
            try:
                # Парсинг задачи

                task_data = json.loads(task_json)
                server_ip = task_data.get("server_ip")
                chat_id = task_data.get("chat_id")
                logging.info(f"обработка задачи {task_data}")
                # Проверка наличия имени сервера
                server_name = get_server_name_by_ip(server_data, server_ip)

                if server_name != "Unknown_Server":
                    # Если имя сервера найдено, добавляем задачу в новую очередь

                    new_queue_name = f"queue_task_{server_name}"

                    await redis_client.rpush(new_queue_name, json.dumps(task_data))
                    logging.info(f"Задача перемещена в очередь с новым именем {new_queue_name}: {task_data}")
                    try:
                        us = await UserCl.load_user(chat_id)
                        await us.active_server.name_server.set(server_name)
                        logging.info(f"Успешная  перезаписи name_server у chat_id = {chat_id}, на  name_server = {server_name}")
                    except Exception as task_error:
                        logging.error(f"Ошибка перезаписи name_server у chat_id = {chat_id}")
                    # Удаляем задачу из старой очереди
                    await redis_client.lrem(queue_name, 1, task_json)
                else:
                    logging.info(f"Имя сервера остается Unknown_Server для задачи: {task_data}")

            except Exception as task_error:
                logging.error(f"Ошибка обработки задачи {task_json}: {task_error}")

    except Exception as e:
        logging.error(f"Ошибка обработки очереди {queue_name}: {e}")
    finally:
        if redis_client:
            await redis_client.close()

def get_server_name_by_ip(server_data, ip_address: str) -> str:
    """Получает имя сервера по его IP."""
    for server in server_data.get("servers", []):
        if server.get("address") == ip_address:
            return server.get("name", "Unknown_Server")
    return "Unknown_Server"