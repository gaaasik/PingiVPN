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
REDIS_HOST = os.getenv('ip_redis_server')  # IP-адрес Redis   queue_results_task
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
        disabled = data.get('disabled')
        transfer_received = data.get('transfer_received')
        transfer_sent = data.get('transfer_sent')
        latest_handshake = data.get('latest_handshake')

        us = await UserCl.load_user(chat_id)

        if data.get('enable') == None:
            await send_admin_log(bot, f"😈Пользователь {chat_id} НЕ изменил состояние, сейчас {us.active_server.enable.get()}, а пришло NONE status={status}")
        else:
            enable = data.get('enable')
            await send_admin_log(bot, f"😈Пользователь {chat_id} изменил состояние на {enable}, status={status}")





        # if not all([chat_id, user_ip]):
        #     logging.error(f"Отсутствуют обязательные параметры в JSON: {data}")
        #     return  # Прерываем выполнение функции, если параметры отсутствуют



        us = await UserCl.load_user(chat_id)

        # Обновляем значения в базе данных только если они не равны "no_parameter"
        if enable != "no_parameter" and enable != None:
            logging.info(f"Запуск set_enable_admin из process_updata_traffic!!!!!!!!!!!!")
            await us.active_server.enable.set_enable_admin(enable)
        else:
            logging.info("enable имеет значение 'no_parameter', пропускаем обновление.")

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

