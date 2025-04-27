import asyncio
import json
import redis.asyncio as redis
from logging_config.my_logging import my_logging
from task_processor.server_settings import ServerSettings
from task_processor.task_manager import TaskManager

async def notify_server_rebooted():
    redis_client = await ServerSettings.get_redis_client()
    result = {
        "status": "alive",
        "task_type": "result_update_and_reboot_server",
        "server_name": ServerSettings.SERVER_NAME,
        "server_ip": ServerSettings.SERVER_IP,
    }
    await redis_client.lpush(ServerSettings.NAME_RESULT_QUEUE, json.dumps(result))
    my_logging.info(f"🔔 Уведомление о перезапуске отправлено: {result}")

async def process_tasks():
    """Обрабатывает задачи из Redis в бесконечном цикле."""
    await ServerSettings.initialize()  # Инициализация настроек сервера при обработке очереди

    redis_client = await ServerSettings.get_redis_client()
    task_manager = TaskManager()
    name_task_queue = ServerSettings.NAME_TASK_QUEUE

    await notify_server_rebooted()
    my_logging.info(f"Слушаю очередь задач: {name_task_queue}")

    while True:
        try:
            task_data = await redis_client.blpop(name_task_queue, timeout=0)
            if task_data:
                _, task_data = task_data
                task_json = json.loads(task_data)
                my_logging.info(f"Извлечена задача из Redis: {task_json}")
                await task_manager.process_task(task_json)
        except redis.ConnectionError as e:
            my_logging.error(f"Ошибка подключения к Redis: {e}. Повторная попытка через 5 секунд...")
            await asyncio.sleep(5)
            continue
        except Exception as e:
            my_logging.error(f"Ошибка обработки задачи: {e}")


async def main():
    """Главная точка входа в программу."""
    await process_tasks()


if __name__ == "__main__":
    asyncio.run(main())
