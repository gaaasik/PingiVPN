# import asyncio
# import aiohttp
# import aioredis
# import json
# import logging
# from asyncio import Semaphore
#
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
#
# REDIS_QUEUE_NAME = "send_3x_ui"
# REDIS_URL = "redis://localhost:6379"
# CHECK_INTERVAL_NO_TASKS = 300  # Интервал проверки доступности сервера при отсутствии задач (5 минут)
# CHECK_INTERVAL_WITH_TASKS = 5  # Интервал проверки очереди при наличии задач (5 секунд)
# SHORT_CHECK_INTERVAL = 2  # Интервал 2 секунды при большом количестве задач
# RETRY_INTERVAL_SHORT = 10  # Интервал 10 секунд после неудачной отправки
# RETRY_INTERVAL_LONG = 300  # Интервал 5 минут после 12 неудачных попыток
# MAX_RETRIES = 12  # Максимальное количество попыток после неудачи
# MAX_TASKS_PER_CYCLE = 100  # Количество задач на пакет
# MAX_CONCURRENT_REQUESTS = 100  # Максимальное количество параллельных запросов
#
#
# async def is_server_available(server_ip):
#     """Проверяет доступность сервера на основе server_ip."""
#     url = f"http://{server_ip}:6222/api/update-enable"
#     try:
#         async with aiohttp.ClientSession() as session:
#             async with session.get(url, timeout=5) as response:
#                 return response.status == 200
#     except (aiohttp.ClientConnectionError, aiohttp.ServerDisconnectedError, asyncio.TimeoutError):
#         return False
#
#
# async def send_json_to_3xui(data, semaphore):
#     """Отправляет JSON на сервер 3x-ui с использованием указанного server_ip."""
#     server_ip = data.get("server_ip")
#     url = f"http://{server_ip}:6222/api/update-enable"
#     headers = {"Content-Type": "application/json"}
#     timeout = aiohttp.ClientTimeout(total=20)
#
#     async with semaphore:
#         try:
#             async with aiohttp.ClientSession(timeout=timeout) as session:
#                 async with session.post(url, json=data, headers=headers) as response:
#                     if response.status == 200:
#                         logger.info(f"JSON успешно отправлен на сервер {server_ip}.")
#                         return True
#                     else:
#                         logger.error(
#                             f"Ошибка отправки JSON на сервер {server_ip}: {response.status}. Ответ сервера: {await response.text()}")
#                         return False
#         except aiohttp.ClientConnectionError:
#             logger.error(f"Ошибка подключения к серверу {server_ip}.")
#             return False
#         except aiohttp.ServerDisconnectedError:
#             logger.error(f"Сервер {server_ip} разорвал соединение.")
#             return False
#         except asyncio.TimeoutError:
#             logger.error("Запрос завершен по тайм-ауту.")
#             return False
#         except aiohttp.ClientError as e:
#             logger.error(f"Ошибка при отправке JSON: {e}")
#             return False
#
#
# async def process_task_queue():
#     """Обрабатывает задачи из очереди Redis с адаптивной проверкой доступности сервера и пакетной обработкой."""
#     redis = aioredis.from_url(REDIS_URL, db=1)
#     retries = 0  # Счётчик попыток при недоступности сервера
#     semaphore = Semaphore(MAX_CONCURRENT_REQUESTS)  # Ограничение параллелизма
#
#     try:
#         while True:
#             # Проверка очереди Redis на количество задач
#             queue_length = await redis.llen(REDIS_QUEUE_NAME)
#             check_interval = SHORT_CHECK_INTERVAL if queue_length > 50 else CHECK_INTERVAL_WITH_TASKS
#
#             if queue_length > 0:
#                 # Извлекаем первую задачу, чтобы получить server_ip для проверки доступности
#                 task_json = await redis.lpop(REDIS_QUEUE_NAME)
#                 if task_json:
#                     task_data = json.loads(task_json)
#                     server_ip = task_data.get("server_ip")
#
#                     # Проверяем доступность сервера, если он недоступен, используем retries
#                     if retries == 0 or await is_server_available(server_ip):
#                         logger.info(f"Сервер {server_ip} доступен, начинаем отправку задач.")
#                         retries = 0  # Сброс счётчика при успешной проверке доступности
#
#                         # Собираем пакет задач с тем же server_ip
#                         tasks_to_send = [task_data]
#                         for _ in range(min(queue_length, MAX_TASKS_PER_CYCLE - 1)):
#                             task_json = await redis.lpop(REDIS_QUEUE_NAME)
#                             if task_json:
#                                 next_task_data = json.loads(task_json)
#                                 # Проверяем, что server_ip совпадает
#                                 if next_task_data.get("server_ip") == server_ip:
#                                     tasks_to_send.append(next_task_data)
#                                 else:
#                                     # Если другой server_ip, возвращаем задачу в очередь и выходим
#                                     await redis.lpush(REDIS_QUEUE_NAME, task_json)
#                                     break
#
#                         # Параллельная отправка задач на server_ip
#                         logger.info(f"Отправляем пакет из {len(tasks_to_send)} задач на сервер {server_ip}.")
#                         send_tasks = [send_json_to_3xui(task, semaphore) for task in tasks_to_send]
#                         results = await asyncio.gather(*send_tasks)
#
#                         # Проверка результата отправки
#                         if not all(results):
#                             retries = 1
#                             logger.info(
#                                 f"Неудачная отправка на сервер {server_ip}. Начинаем частую проверку доступности каждые {RETRY_INTERVAL_SHORT} секунд.")
#                             await asyncio.sleep(RETRY_INTERVAL_SHORT)
#
#                     else:
#                         # Если сервер недост
#                         # упен, увеличиваем интервал проверки
#                         if retries < MAX_RETRIES:
#                             retries += 1
#                             logger.warning(
#                                 f"Сервер {server_ip} недоступен. Попытка {retries}/{MAX_RETRIES}. Повторная проверка через {RETRY_INTERVAL_SHORT} секунд.")
#                             await asyncio.sleep(RETRY_INTERVAL_SHORT)
#                         else:
#                             logger.warning(
#                                 f"Сервер {server_ip} недоступен. Переход на долгий интервал проверки (5 минут).")
#                             await asyncio.sleep(RETRY_INTERVAL_LONG)
#
#             else:
#                 # Если задач нет, проверяем доступность сервера каждые 5 минут
#                 logger.info("Задач в очереди нет. Проверка доступности сервера через 5 минут.")
#                 await asyncio.sleep(CHECK_INTERVAL_NO_TASKS)
#
#     except Exception as e:
#         logger.error(f"Ошибка при обработке задач из очереди: {e}")
#     finally:
#         await redis.close()
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
# #
# # logging.basicConfig(level=logging.INFO)
# # logger = logging.getLogger(__name__)
# #
# #
# # async def send_json_to_3xui(data):
# #     url = "http://194.87.208.18:6222/api/update-enable"
# #     headers = {"Content-Type": "application/json"}
# #     timeout = aiohttp.ClientTimeout(total=20)  # Добавляем тайм-аут в 10 секунд
# #
# #     logger.info("Попытка подключения и отправки JSON на сервер 3x-ui...")
# #
# #     try:
# #         async with aiohttp.ClientSession(timeout=timeout) as session:
# #             async with session.post(url, json=data, headers=headers) as response:
# #                 if response.status == 200:
# #                     logger.info("JSON успешно отправлен на сервер 3x-ui.")
# #                 else:
# #                     error_text = await response.text()
# #                     logger.error(f"Ошибка отправки JSON: {response.status}. Ответ сервера: {error_text}")
# #     except aiohttp.ClientConnectorError as e:
# #         logger.error("Ошибка подключения к серверу 3x-ui. Проверьте доступность сервера.")
# #         logger.error(f"Детали ошибки: {e}")
# #     except aiohttp.ClientOSError as e:
# #         logger.error("Произошла ошибка связи с сервером 3x-ui.")
# #         logger.error(f"Детали ошибки: {e}")
# #     except asyncio.TimeoutError:
# #         logger.error("Запрос завершен по тайм-ауту.")
# #     except Exception as e:
# #         logger.error(f"Непредвиденная ошибка при отправке JSON: {e}")
# #
# # # Настройка логирования
# #
# #
# #
# # async def process_task_queue():
# #     """Функция для обработки задач из очереди Redis и отправки их на сервер 3x-ui."""
# #     redis = aioredis.from_url("redis://localhost", db=1)
# #
# #     try:
# #         while True:
# #             # Логирование попытки извлечения задачи из очереди
# #             logger.info("Попытка извлечь задачу из очереди Redis.")
# #
# #             task_json = await redis.lpop("send_3x_ui")
# #             if task_json:
# #                 task_data = json.loads(task_json)
# #
# #                 # Логирование успешного извлечения задачи
# #                 logger.info(f"Извлечена задача: {task_data}")
# #
# #                 await send_json_to_3xui(task_data)
# #             else:
# #                 # Логирование в случае, если очередь пуста
# #                 logger.info("Очередь пуста, следующая попытка через 5 секунд.")
# #
# #                 await asyncio.sleep(5)
# #     except Exception as e:
# #         # Логирование любых ошибок, возникающих при обработке задачи
# #         logger.error(f"Ошибка при обработке задачи из очереди: {e}")
# #     finally:
# #         await redis.close()
