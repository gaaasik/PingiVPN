import asyncio
import json
import logging
import os
import traceback

from .result_task_manager import ResultTaskManager
from redis_configs.redis_settings import redis_client
from redis.exceptions import ConnectionError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def process_queue_results_task():
    """Асинхронное прослушивание очереди Redis и обработка задач. push"""
    manager = ResultTaskManager(redis_client)
    logging.info("Запущено прослушивание очереди result_task_queue.")
    NAME_RESULT_QUEUE = os.getenv("name_queue_result_task").strip()

    while True:
        try:
            task_data = await redis_client.blpop(NAME_RESULT_QUEUE, timeout=0)
            if task_data:
                try:

                    task_json = json.loads(task_data[1])

                    logging.info(f"Получена задача: {task_json}")
                    await manager.process_task(task_json)
                except json.JSONDecodeError as e:
                    logging.error(f"Ошибка декодирования JSON: {e}")
        except ConnectionError as e:
            logging.error(f"Redis Connection Error: {e}")
            # Можно переинициализировать redis_client или подождать перед повторной попыткой
            await asyncio.sleep(5)
        except Exception as e:
            logging.error(f"Ошибка при обработке очереди: {e}")
            await asyncio.sleep(5)
