import asyncio
import json
import logging
from result_task_manager import ResultTaskManager
from redis_configs.redis_settings import redis_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


async def process_queue_results_task():
    """Асинхронное прослушивание очереди Redis и обработка задач."""
    manager = ResultTaskManager(redis_client)
    logging.info("Запущено прослушивание очереди result_task_queue.")

    while True:
        try:
            task_data = await redis_client.blpop("queue_result_task", timeout=0)
            if task_data:
                try:
                    task_json = json.loads(task_data[1])
                    logging.info(f"Получена задача: {task_json}")
                    await manager.process_task(task_json)
                except json.JSONDecodeError as e:
                    logging.error(f"Ошибка декодирования JSON: {e}")
        except Exception as e:
            logging.error(f"Ошибка при обработке очереди: {e}")
            await asyncio.sleep(5)
