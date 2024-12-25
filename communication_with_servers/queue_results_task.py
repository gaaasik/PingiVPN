import os
import asyncio
import json
import logging
import redis.asyncio as redis
from dotenv import load_dotenv

from bot.handlers.admin import send_admin_log
from bot_instance import bot
from models.UserCl import UserCl

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("main_server_task_processor.log"),
        logging.StreamHandler()
    ]
)

load_dotenv()

# Настройки Redis
REDIS_HOST = os.getenv('ip_redis_server')  # IP-адрес Redis
REDIS_PORT = int(os.getenv('port_redis'))  # Порт Redis
REDIS_PASSWORD = os.getenv('password_redis')  # Пароль Redis (если требуется)
NAME_RESULT_QUEUE = "queue_result_task"

# Инициализация асинхронного клиента Redis
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, decode_responses=True)

async def process_task(task):
    """Обработка задачи."""
    try:
        logging.info("Начало обработки задачи.")
        task_data = json.loads(task)
        logging.info(f"Получена задача для обработки: {task_data}")

        if task_data.get("status") == "success":
            logging.info(f"Задача успешно выполнена: {task_data}")
        elif task_data.get("status") == "error":
            logging.error(f"Ошибка при выполнении задачи: {task_data}")
        else:
            logging.warning(f"Неизвестный статус задачи: {task_data}")
    except json.JSONDecodeError as e:
        logging.error(f"Ошибка декодирования задачи: {e}")
    except Exception as e:
        logging.error(f"Ошибка обработки задачи: {e}")
    finally:
        logging.info("Завершение обработки задачи.")

async def process_queue_results_task():
    """Асинхронное прослушивание очереди Redis."""
    logging.info("Начало прослушивания очереди tasks")
    while True:
        try:
            # Получаем задачу из очереди
            task_data = await redis_client.lpop(NAME_RESULT_QUEUE)
            if task_data:
                logging.info(f"Извлечена задача из Redis: {task_data}")
                try:
                    task = json.loads(task_data)
                    logging.info(f"Задача после парсинга JSON: {task}")
                except json.JSONDecodeError as e:
                    logging.error(f"Ошибка декодирования JSON: {e}, данные: {task_data}")
                    continue


                # Обрабатываем задачу
                await process_updata_traffic(json.dumps(task))
            else:
                await asyncio.sleep(3)  # Пауза перед следующим запросом
        except redis.ConnectionError as e:
            logging.error(f"Ошибка подключения к Redis: {e}")
            await asyncio.sleep(5)
        except Exception as e:
            logging.error(f"Ошибка при обработке сообщения из Redis: {e}")
            await asyncio.sleep(5)

async def process_updata_traffic(json_task):
    """Обработка сообщения из Redis с информацией о трафике."""
    try:
        logging.info("Начинаем обработку сообщения: process_updata_traffic")
        data = json.loads(json_task)
        logging.info(f"Распарсенные данные сообщения: {data}")

        # Извлечение необходимых данных
        status = data.get('status')
        chat_id = data.get('chat_id')
        user_ip = data.get('user_ip')
        enable = data.get('enable')
        disabled = data.get('disabled')
        transfer_received = data.get('transfer_received')
        transfer_sent = data.get('transfer_sent')
        latest_handshake = data.get('latest_handshake')


        await send_admin_log(bot,f"😈Пользователь {chat_id} изменил состояние на {enable}, status={status}")

        if not all([chat_id, user_ip]):
            logging.error(f"Отсутствуют обязательные параметры в JSON: {data}")
            return  # Прерываем выполнение функции, если параметры отсутствуют

        print("Данные с queue_result_task")
        print("status = ", status)
        print("user_ip = ", user_ip)
        print("transfer_received = ", transfer_received)
        print("transfer_sent = ", transfer_sent)
        print("latest_handshake = ", latest_handshake)
        print("chat_id = ", chat_id)
        print("disabled = ", disabled)
        print("enable = ", enable)

        us = await UserCl.load_user(chat_id)

        # Обновляем значения в базе данных только если они не равны "no_parameter"
        if latest_handshake != "no_parameter":
            await us.active_server.date_latest_handshake.set(latest_handshake)
        else:
            logging.info("latest_handshake имеет значение 'no_parameter', пропускаем обновление.")

        if transfer_received != "no_parameter":
            await us.active_server.traffic_up.set(transfer_received)
        else:
            logging.info("transfer_received имеет значение 'no_parameter', пропускаем обновление.")

        if transfer_sent != "no_parameter":
            await us.active_server.traffic_down.set(transfer_sent)
        else:
            logging.info("transfer_sent имеет значение 'no_parameter', пропускаем обновление.")

    except json.JSONDecodeError as e:
        logging.info(f"Ошибка декодирования JSON: {e}, данные: {json_task}")
    except Exception as e:
        logging.info(f"Ошибка при обработке сообщения о трафике: {e}")

# async def process_queue_results_task():
#     logging.info("Запуск обработки очереди...")
#
#     redis = None
#     try:
#         # Подключение к Redis
#         redis = await aioredis.from_url(
#             f"redis://{REDIS_HOST}:{REDIS_PORT}",
#             password=REDIS_PASSWORD,
#             decode_responses=True
#         )
#
#
#         while True:
#             try:
#                 logging.info("Ожидание задачи из Redis...")
#
#                 task = await asyncio.to_thread(redis.lpop, NAME_RESULT_QUEUE)
#
#                 if task:
#                     _, task_data = task
#                     await process_task(task_data)
#                 else:
#                     logging.info("Тайм-аут ожидания задачи. Продолжаем.")
#
#             except asyncio.CancelledError:
#                 logging.info("Получен сигнал отмены задачи. Завершаем...")
#                 break
#             except aioredis.ConnectionError as e:
#                 logging.error(f"Ошибка подключения к Redis: {e}")
#                 await asyncio.sleep(5)  # Переподключение через 5 секунд
#             except Exception as e:
#                 logging.error(f"Непредвиденная ошибка в процессе обработки задачи: {e}")
#     except GeneratorExit as ge:
#         logging.error(f"Завершение генератора: {ge}")
#     except Exception as e:
#         logging.error(f"Непредвиденная ошибка в процессе обработки очереди: {e}")
#     finally:
#         if redis:
#             try:
#                 # Закрытие соединения с Redis
#                 await redis.close()
#                 logging.info("Соединение с Redis закрыто.")
#             except Exception as close_error:
#                 logging.error(f"Ошибка при закрытии соединения Redis: {close_error}")
#
#









# async def process_queue_results_task():
#     logging.info("Запуск обработки очереди...")
#
#     redis = None
#     try:
#         # Подключение к Redis
#         redis = await aioredis.from_url(
#             f"redis://{REDIS_HOST}:{REDIS_PORT}",
#             password=REDIS_PASSWORD,
#             decode_responses=True
#         )
#
#         while True:
#             try:
#                 logging.info("Ожидание задачи из Redis...")
#                 task = await redis.lpop(NAME_RESULT_QUEUE, timeout=5)
#                 if task:
#                     _, task_data = task
#                     await process_task(task_data)
#                 else:
#                     logging.info("Тайм-аут ожидания задачи. Продолжаем.")
#
#             except asyncio.CancelledError:
#                 logging.info("Получен сигнал отмены задачи. Завершаем...")
#                 break
#             except aioredis.ConnectionError as e:
#                 logging.error(f"Ошибка подключения к Redis: {e}")
#                 await asyncio.sleep(5)  # Переподключение через 5 секунд
#             except Exception as e:
#                 logging.error(f"Непредвиденная ошибка в процессе обработки задачи: {e}")
#     except GeneratorExit as ge:
#         logging.error(f"Завершение генератора: {ge}")
#     except Exception as e:
#         logging.error(f"Непредвиденная ошибка в процессе обработки очереди: {e}")
#     finally:
#         if redis:
#             try:
#                 # Закрытие соединения с Redis
#                 await redis.close()
#                 logging.info("Соединение с Redis закрыто.")
#             except Exception as close_error:
#                 logging.error(f"Ошибка при закрытии соединения Redis: {close_error}")




















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
