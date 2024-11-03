import logging

import aioredis
import aiohttp
import asyncio
import json


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def send_json_to_3xui(data):
    url = "http://194.87.208.18:6222/api/update-enable"
    headers = {"Content-Type": "application/json"}
    timeout = aiohttp.ClientTimeout(total=20)  # Добавляем тайм-аут в 10 секунд

    logger.info("Попытка подключения и отправки JSON на сервер 3x-ui...")

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=data, headers=headers) as response:
                if response.status == 200:
                    logger.info("JSON успешно отправлен на сервер 3x-ui.")
                else:
                    error_text = await response.text()
                    logger.error(f"Ошибка отправки JSON: {response.status}. Ответ сервера: {error_text}")
    except aiohttp.ClientConnectorError as e:
        logger.error("Ошибка подключения к серверу 3x-ui. Проверьте доступность сервера.")
        logger.error(f"Детали ошибки: {e}")
    except aiohttp.ClientOSError as e:
        logger.error("Произошла ошибка связи с сервером 3x-ui.")
        logger.error(f"Детали ошибки: {e}")
    except asyncio.TimeoutError:
        logger.error("Запрос завершен по тайм-ауту.")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при отправке JSON: {e}")

# Настройка логирования



async def process_task_queue():
    """Функция для обработки задач из очереди Redis и отправки их на сервер 3x-ui."""
    redis = aioredis.from_url("redis://localhost", db=1)

    try:
        while True:
            # Логирование попытки извлечения задачи из очереди
            logger.info("Попытка извлечь задачу из очереди Redis.")

            task_json = await redis.lpop("send_3x_ui")
            if task_json:
                task_data = json.loads(task_json)

                # Логирование успешного извлечения задачи
                logger.info(f"Извлечена задача: {task_data}")

                await send_json_to_3xui(task_data)
            else:
                # Логирование в случае, если очередь пуста
                logger.info("Очередь пуста, следующая попытка через 5 секунд.")

                await asyncio.sleep(5)
    except Exception as e:
        # Логирование любых ошибок, возникающих при обработке задачи
        logger.error(f"Ошибка при обработке задачи из очереди: {e}")
    finally:
        await redis.close()
#
# async def send_json_to_3xui(data):
#     url = "http://192.87.208.18:6222/api/update-enable"
#     headers = {"Content-Type": "application/json"}
#
#     async with aiohttp.ClientSession() as session:
#         async with session.post(url, json=data, headers=headers) as response:
#             if response.status == 200:
#                 print("JSON успешно отправлен на сервер 3x-ui.")
#             else:
#                 print(f"Ошибка отправки JSON: {response.status}")
#                 error_text = await response.text()
#                 print("Ответ сервера:", error_text)
#
#
# async def process_task_queue():
#     """Функция для обработки задач из очереди Redis и отправки их на сервер 3x-ui."""
#     redis = aioredis.from_url("redis://localhost", db=1)
#
#     try:
#         while True:
#             try:
#                 # Извлекаем задачу из очереди
#                 task_json = await redis.lpop("send_3x_ui")
#
#                 if task_json:
#                     # Преобразуем задачу из JSON в Python-словарь
#                     task_data = json.loads(task_json)
#
#                     # Пытаемся отправить задачу на сервер 3x-ui
#                     await send_json_to_3xui(task_data)
#
#                 else:
#                     # Если задач нет, ждем перед следующей проверкой
#                     await asyncio.sleep(5)
#
#             except Exception as e:
#                 print(f"Ошибка обработки задачи: {e}")
#                 await asyncio.sleep(5)  # Ждем перед повторной попыткой
#
#     finally:
#         await redis.close()
