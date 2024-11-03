import asyncio
import aiohttp
import aioredis
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_QUEUE_NAME = "send_3x_ui"
REDIS_URL = "redis://localhost:6379"
CHECK_INTERVAL_NO_TASKS = 300   # Интервал проверки доступности сервера при отсутствии задач (5 минут)
CHECK_INTERVAL_WITH_TASKS = 5   # Интервал проверки очереди при наличии задач (5 секунд)
SHORT_CHECK_INTERVAL = 2        # Краткий интервал, если задач много (1-2 секунды)
RETRY_INTERVAL_SHORT = 10       # Интервал проверки доступности после неудачной отправки (10 секунд)
RETRY_INTERVAL_LONG = 300       # Долгий интервал проверки после 12 неудачных попыток (5 минут)
MAX_RETRIES = 12                # Максимальное количество попыток проверки доступности после неудачи
MAX_TASKS_PER_CYCLE = 10        # Лимит задач за один цикл отправки для балансировки нагрузки

async def is_server_available(url):
    """Проверяет доступность сервера."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                return response.status == 200
    except (aiohttp.ClientConnectionError, aiohttp.ServerDisconnectedError, asyncio.TimeoutError):
        return False

async def send_json_to_3xui(data):
    """Отправляет JSON на сервер 3x-ui."""
    url = "http://194.87.208.18:6222/api/update-enable"
    headers = {"Content-Type": "application/json"}
    timeout = aiohttp.ClientTimeout(total=20)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=data, headers=headers) as response:
                if response.status == 200:
                    logger.info("JSON успешно отправлен на сервер 3x-ui.")
                    return True
                else:
                    logger.error(f"Ошибка отправки JSON: {response.status}. Ответ сервера: {await response.text()}")
                    return False
    except aiohttp.ClientConnectionError:
        logger.error("Ошибка подключения к серверу 3x-ui.")
        return False
    except aiohttp.ServerDisconnectedError:
        logger.error("Сервер 3x-ui разорвал соединение.")
        return False
    except asyncio.TimeoutError:
        logger.error("Запрос завершен по тайм-ауту.")
        return False
    except aiohttp.ClientError as e:
        logger.error(f"Ошибка при отправке JSON: {e}")
        return False

async def process_task_queue():
    """Обрабатывает задачи из очереди Redis с адаптивной проверкой доступности сервера."""
    redis = aioredis.from_url(REDIS_URL, db=1)
    url_to_check = "http://194.87.208.18:6222/api/update-enable"
    retries = 0  # Счётчик попыток при недоступности сервера

    try:
        while True:
            # Проверяем длину очереди и устанавливаем интервал проверки в зависимости от количества задач
            queue_length = await redis.llen(REDIS_QUEUE_NAME)
            if queue_length > 50:
                check_interval = SHORT_CHECK_INTERVAL  # Быстрая проверка, если задач много
            else:
                check_interval = CHECK_INTERVAL_WITH_TASKS

            # Проверяем наличие задач в очереди
            task_json = await redis.lpop(REDIS_QUEUE_NAME)
            if task_json:
                # Есть задача, проверяем доступность сервера разово
                if retries == 0 or await is_server_available(url_to_check):
                    logger.info("Сервер доступен, начинаем отправку задач.")
                    retries = 0  # Сброс счётчика при первой успешной проверке доступности

                    # Начинаем отправку задач
                    task_data = json.loads(task_json)
                    tasks_sent = 0
                    while await send_json_to_3xui(task_data):
                        tasks_sent += 1
                        logger.info(f"Задача {tasks_sent} отправлена: {task_data}")

                        # Если отправлено больше MAX_TASKS_PER_CYCLE задач, делаем паузу
                        if tasks_sent >= MAX_TASKS_PER_CYCLE:
                            logger.info("Достигнут лимит задач за цикл, делаем паузу.")
                            await asyncio.sleep(1)
                            tasks_sent = 0  # Сбрасываем счётчик задач за цикл

                        # Переход к следующей задаче без проверки доступности
                        task_json = await redis.lpop(REDIS_QUEUE_NAME)
                        if not task_json:
                            logger.info(f"Очередь пуста, следующая проверка через {check_interval} секунд.")
                            await asyncio.sleep(check_interval)
                            break
                        task_data = json.loads(task_json)

                    # Если отправка не удалась, начинаем частую проверку доступности
                    retries = 1
                    logger.info(f"Отправка не удалась, начинаем частую проверку доступности каждые {RETRY_INTERVAL_SHORT} секунд.")
                    await asyncio.sleep(RETRY_INTERVAL_SHORT)

                else:
                    # Если сервер недоступен, проверяем доступность с увеличивающимся интервалом
                    if retries < MAX_RETRIES:
                        retries += 1
                        logger.warning(f"Сервер недоступен. Попытка {retries}/{MAX_RETRIES}. Повторная проверка через {RETRY_INTERVAL_SHORT} секунд.")
                        await asyncio.sleep(RETRY_INTERVAL_SHORT)
                    else:
                        # После MAX_RETRIES попыток проверяем доступность каждые 5 минут
                        logger.warning("Сервер по-прежнему недоступен. Переход на долгий интервал проверки (5 минут).")
                        await asyncio.sleep(RETRY_INTERVAL_LONG)

            else:
                # Если задач нет, проверяем доступность сервера каждые 5 минут
                logger.info("Задач в очереди нет. Проверка доступности сервера через 5 минут.")
                await asyncio.sleep(CHECK_INTERVAL_NO_TASKS)

    except Exception as e:
        logger.error(f"Ошибка при обработке задачи из очереди: {e}")
    finally:
        await redis.close()







































#
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
#
#
# async def send_json_to_3xui(data):
#     url = "http://194.87.208.18:6222/api/update-enable"
#     headers = {"Content-Type": "application/json"}
#     timeout = aiohttp.ClientTimeout(total=20)  # Добавляем тайм-аут в 10 секунд
#
#     logger.info("Попытка подключения и отправки JSON на сервер 3x-ui...")
#
#     try:
#         async with aiohttp.ClientSession(timeout=timeout) as session:
#             async with session.post(url, json=data, headers=headers) as response:
#                 if response.status == 200:
#                     logger.info("JSON успешно отправлен на сервер 3x-ui.")
#                 else:
#                     error_text = await response.text()
#                     logger.error(f"Ошибка отправки JSON: {response.status}. Ответ сервера: {error_text}")
#     except aiohttp.ClientConnectorError as e:
#         logger.error("Ошибка подключения к серверу 3x-ui. Проверьте доступность сервера.")
#         logger.error(f"Детали ошибки: {e}")
#     except aiohttp.ClientOSError as e:
#         logger.error("Произошла ошибка связи с сервером 3x-ui.")
#         logger.error(f"Детали ошибки: {e}")
#     except asyncio.TimeoutError:
#         logger.error("Запрос завершен по тайм-ауту.")
#     except Exception as e:
#         logger.error(f"Непредвиденная ошибка при отправке JSON: {e}")
#
# # Настройка логирования
#
#
#
# async def process_task_queue():
#     """Функция для обработки задач из очереди Redis и отправки их на сервер 3x-ui."""
#     redis = aioredis.from_url("redis://localhost", db=1)
#
#     try:
#         while True:
#             # Логирование попытки извлечения задачи из очереди
#             logger.info("Попытка извлечь задачу из очереди Redis.")
#
#             task_json = await redis.lpop("send_3x_ui")
#             if task_json:
#                 task_data = json.loads(task_json)
#
#                 # Логирование успешного извлечения задачи
#                 logger.info(f"Извлечена задача: {task_data}")
#
#                 await send_json_to_3xui(task_data)
#             else:
#                 # Логирование в случае, если очередь пуста
#                 logger.info("Очередь пуста, следующая попытка через 5 секунд.")
#
#                 await asyncio.sleep(5)
#     except Exception as e:
#         # Логирование любых ошибок, возникающих при обработке задачи
#         logger.error(f"Ошибка при обработке задачи из очереди: {e}")
#     finally:
#         await redis.close()
