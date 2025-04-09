import json
import logging

from bot.handlers.admin import send_admin_log
from bot_instance import bot
from models.UserCl import UserCl
from models.country_server_data import get_name_server_by_ip
from redis_configs.redis_settings import redis_client_main

logger = logging.getLogger(__name__)


class QueueErrorHandler:
    def __init__(self):
        self.redis_client_main = redis_client_main

    async def remove_tasks_from_queue(self, server_ip: str, task_type: str):
        """
        Удаляет задачи указанного типа из очереди Redis по IP сервера. не все сервера

        :param server_ip: IP-адрес сервера.
        :param task_type: Тип задачи, которую нужно удалить (например, "update_and_reboot_server").
        """
        try:
            server_name = await get_name_server_by_ip(server_ip)
            if not server_name:
                logger.warning(f"Не удалось найти имя сервера по IP: {server_ip}")
                return

            queue_name = f"queue_task_{server_name}"
            tasks = await self.redis_client_main.lrange(queue_name, 0, -1)
            updated_tasks = []

            for task in tasks:
                try:
                    task_data = json.loads(task)
                except Exception:
                    updated_tasks.append(task)
                    continue

                if not isinstance(task_data, dict) or task_data.get("task_type") != task_type:
                    updated_tasks.append(task)
                else:
                    name_server = await get_name_server_by_ip(task_data.get("server_ip"))
                    await send_admin_log(bot, f"Задача {task_type} удалена для {name_server}-{task_data.get('server_ip')}")

            # Обновление очереди
            await self.redis_client_main.delete(queue_name)
            if updated_tasks:
                await self.redis_client_main.rpush(queue_name, *updated_tasks)
                logger.info(
                    f"[Очередь: {queue_name}] Удалено задач типа '{task_type}': {len(tasks) - len(updated_tasks)}"
                )
            else:
                logger.info(
                    f"[Очередь: {queue_name}] Все задачи типа '{task_type}' удалены"
                )

        except Exception as e:
            logger.error(f"Ошибка при удалении задач из очереди Redis: {e}")
        finally:
            if self.redis_client_main:
                await self.redis_client_main.aclose()


    async def process_unknown_server_queue(self):
        """Обрабатывает очередь `queue_task_Unknown_Server` и перемещает задачи с известными именами серверов."""
        try:
            logging.info(f"Запустился процесс обработки очереди queue_task_Unknown_Server")

            # Получение всех задач из очереди `queue_task_Unknown_Server`
            queue_name = "queue_task_Unknown_Server"
            tasks = await redis_client_main.lrange(queue_name, 0, -1)

            for task_json in tasks:
                try:
                    # Парсинг задачи

                    task_data = json.loads(task_json)
                    server_ip = task_data.get("server_ip")
                    chat_id = task_data.get("chat_id")
                    logging.info(f"обработка задачи {task_data}")
                    # Проверка наличия имени сервера
                    server_name = get_name_server_by_ip(server_ip)

                    if server_name != "Unknown_Server":
                        # Если имя сервера найдено, добавляем задачу в новую очередь Update id=

                        new_queue_name = f"queue_task_{server_name}"

                        await self.redis_client_main.rpush(new_queue_name, json.dumps(task_data))
                        logging.info(f"Задача перемещена в очередь с новым именем {new_queue_name}: {task_data}")
                        try:
                            us = await UserCl.load_user(chat_id)
                            await us.active_server.name_server.set(server_name)
                            logging.info(f"Успешная  перезаписи name_server у chat_id = {chat_id}, на  name_server = {server_name}")
                        except Exception as task_error:
                            logging.error(f"Ошибка перезаписи name_server у chat_id = {chat_id}")
                        # Удаляем задачу из старой очереди
                        await self.redis_client_main.lrem(queue_name, 1, task_json)
                    else:
                        logging.info(f"Имя сервера остается Unknown_Server для задачи: {task_data}")

                except Exception as task_error:
                    logging.error(f"Ошибка обработки задачи {task_json}: {task_error}")
        except Exception as e:
            logging.error(f"Ошибка обработки очереди {queue_name}: {e}")
        finally:
            if self.redis_client_main:
                await self.redis_client_main.close()
