import asyncio
import json
from abc import ABC, abstractmethod
from typing import Dict

import redis

from logging_config.my_logging import my_logging
from task_processor.server_settings import ServerSettings


class VPNProcessor(ABC):
    """Абстрактный класс для обработки VPN-задач."""

    @abstractmethod
    async def process_change_enable_user(self, task_data: Dict):
        pass

    @abstractmethod
    async def get_user_traffic(self, user_identifier: str) -> Dict:
        pass

    @abstractmethod
    async def get_user_enable_status(self, user_identifier: str) -> bool:
        pass

    @abstractmethod
    async def process_delete_user(self, task_data: Dict):
        pass

    @abstractmethod
    async def creating_user(self, task_data: Dict, count_users: int):
        pass

    @abstractmethod
    async def get_count_true_user(self) -> int:
        pass

    async def process_creating_user(self, task_data: Dict):
        count_true_user = await self.get_count_true_user()
        count_new_user = ServerSettings.SERVER_COUNT_USERS - count_true_user if ServerSettings.SERVER_COUNT_USERS - count_true_user > 0 else 0

        if count_true_user:
            my_logging.info(f"Генерируем {count_new_user} пользователей")
            await self.creating_user(task_data, count_new_user)
        else:
            my_logging.info(f"Пользователей не генерируем, мест тену")


    async def process_check_enable_user(self, task_data: Dict):
        """Проверяет состояние пользователя и обновляет его в Redis, если оно изменилось."""

        try:
            expected_enable = task_data.get("enable")
            protocol = task_data.get("name_protocol")
            chat_id = task_data.get("chat_id")

            my_logging.info(f"Проверка enable пользователя: {chat_id}")
            # Определяем, какой идентификатор использовать
            if protocol == "wireguard":
                user_identifier = task_data.get("user_ip")
            elif protocol == "vless":
                user_identifier = task_data.get("uuid_value")
            else:
                my_logging.error(f"Неизвестный протокол {protocol} в задаче: {task_data}")
                return

            # Проверяем, есть ли все необходимые данные в задаче
            if not user_identifier or expected_enable is None:
                my_logging.error(f"Некорректные данные в задаче check_enable_user: {task_data}")
                return

            # Получаем текущее состояние пользователя
            current_enable = await self.get_user_enable_status(user_identifier)
            if current_enable == expected_enable:
                my_logging.info(f"Состояние пользователя {user_identifier} ({protocol}) не изменилось.")
                return

            # Если состояние изменилось, отправляем обновленные данные в Redis
            redis_client = await ServerSettings.get_redis_client()
            result = {
                "status": "new_data",
                "task_type": "result_check_enable_user",
                "enable": current_enable,
                "user_ip": task_data.get("user_ip"),
                "uuid_value": task_data.get("uuid_value"),
                "protocol": protocol,
                "chat_id": chat_id,
            }
            await redis_client.lpush(ServerSettings.NAME_RESULT_QUEUE, json.dumps(result))
            my_logging.info(f"Обновленные данные отправлены в Redis: {result}")
        except redis.RedisError as e:
            my_logging.error(f"Ошибка подключения к Redis: {e}. Повторная попытка через 5 секунд...")
            await asyncio.sleep(5)
        except Exception as e:
            my_logging.error(f"Ошибка при проверке enable пользователя {user_identifier}: {e}")

    async def process_update_and_reboot_server(self, task_data: Dict):
        await self.run_system_update()  # Ждём окончания
        await asyncio.sleep(5)  # На всякий случай
        await self.reboot_server()  # После полной уверенности

    async def run_system_update(self):
        """Запускает обновление системы и дожидается завершения фоновых установок."""

        command = "sudo apt update && sudo apt upgrade -y"
        try:
            my_logging.info("🚀 Запускаем обновление системы...")
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if stdout:
                my_logging.info(f"📦 Вывод apt:\n{stdout.decode()}")
            if stderr:
                my_logging.warning(f"⚠️ Предупреждения apt:\n{stderr.decode()}")

            my_logging.info("⏳ Проверяем, завершились ли процессы dpkg/apt...")

            while True:
                check_proc = await asyncio.create_subprocess_shell(
                    "pgrep -x apt || pgrep -x dpkg",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                out, _ = await check_proc.communicate()

                if not out.decode().strip():
                    my_logging.info("✅ Все фоновые процессы завершены.")
                    break

                my_logging.info("⏳ Обновление всё ещё идёт... Ждём 5 секунд.")
                await asyncio.sleep(5)

        except Exception as e:
            my_logging.error(f"❌ Ошибка при обновлении системы: {e}")

    async def reboot_server(self):
        """Перезагружает сервер."""
        try:
            my_logging.info("🔄 Перезагрузка сервера...")
            await asyncio.create_subprocess_shell("sudo reboot")
        except Exception as e:
            my_logging.error(f"❌ Ошибка при попытке перезагрузки сервера: {e}")