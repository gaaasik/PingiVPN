import json
import asyncio
import logging
import os

import aioredis
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from bot.admin_func.history_key.moving_wg_files import generate_qr_code
from bot.handlers.admin import send_admin_log
from bot_instance import bot
from communication_with_servers.result_processor.all_processor.base_processor import BaseResultProcessor


load_dotenv()
# 📌 Путь к файлу с URL
URL_FILE_PATH = Path("configs/url_vless_new")
REDIS_KEY = "daily_created_users"  # 🔥 Ключ для хранения числа новых пользователей в Redis
CONFIGS_DIR = os.getenv('CONFIGS_DIR')
BASE_CONFIGS_DIR = os.path.join(CONFIGS_DIR, 'base_configs')

class ResultCreateUsers(BaseResultProcessor):
    """Обработчик результата создания пользователей VLESS."""

    async def process(self, task_data: dict):
        """
        📌 Обрабатывает результат создания пользователей.
        """
        logging.info(f"Начало обработки результата создания пользователей: {task_data}")

        status = task_data.get("status", "error")
        server_name = task_data.get("server_name", "unknown")
        protocol = task_data.get("protocol", "unknown")
        server_ip = task_data.get("server_ip", "unknown")
        count_users = task_data.get("count_users", 0)


        if status == "success":

            logging.info(f"📌 Созданные пользователи: {count_users}")

            if protocol == "wireguard":
                all_users = task_data.get("created_users", [])
                await self.append_files_wg_to_user(all_users)
                message = f"Успешно создано {count_users} пользователей WG {all_users}"
            # 📌 Добавляем URL в файл и увеличиваем счетчик в Redis
            elif protocol == "vless":

                all_urls = task_data.get("all_urls", [])
                await self.append_urls_to_file(all_urls)
                message = f"Успешно создано {count_users} пользователей.\n\n🔗 Ссылки на VLESS:\n" + "\n".join(all_urls)
            #await self.increment_user_count(count_users)

        else:
            message = f"Ошибка при создании пользователей!\n\n{task_data.get('message', 'Неизвестная ошибка')}"
            logging.error("Ошибка при обработке result_create_users")
            await send_admin_log(bot,f"result_creating_user \n{message}")

        # 🚀 Отправляем сообщение в Telegram или логируем
        logging.info(f"📨 Сообщение отправлено в Telegram: {message}")

    async def append_files_wg_to_user(self, all_users):
        """
        Сохраняет .conf и QR-файлы для каждого пользователя WireGuard,
        если все необходимые данные присутствуют.
        """
        try:
            Path(BASE_CONFIGS_DIR).mkdir(parents=True, exist_ok=True)

            for user in all_users:
                required_fields = [
                    "name", "private_key", "address", "dns",
                    "server_public_key", "pre_shared_key", "endpoint"
                ]

                # Проверка, что все поля присутствуют и не пустые
                missing = [field for field in required_fields if not user.get(field)]
                if missing:
                    logging.error(
                        f"Пропущено создание конфига для пользователя {user.get('name', 'unknown')}: отсутствуют поля {missing}")
                    continue  # Пропускаем этого пользователя

                name = user["name"]
                conf_path = Path(BASE_CONFIGS_DIR) / f"{name}.conf"
                qr_path = Path(BASE_CONFIGS_DIR) / f"{name}.png"

                conf_content = f"""[Interface]
PrivateKey = {user["private_key"]}
Address = {user["address"]}/24
DNS = {user["dns"]}

[Peer]
PublicKey = {user["server_public_key"]}
PresharedKey = {user["pre_shared_key"]}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 0
Endpoint = {user["endpoint"]}
    """

                # Сохраняем .conf
                with open(conf_path, "w", encoding="utf-8") as f:
                    f.write(conf_content)
                logging.info(f"📄 Конфигурация сохранена: {conf_path}")

                # Генерируем QR
                await generate_qr_code(conf_path, qr_path)

        except Exception as e:
            logging.error(f"Ошибка при генерации конфигов или QR-кодов: {e}")

    async def append_urls_to_file(self, urls: list):
        """
        📌 Добавляет новые URL в файл `url_vless_new`, но **НЕ** хранит число.
        """
        try:
            if not URL_FILE_PATH.exists():
                URL_FILE_PATH.touch()

            async with asyncio.Lock():  # 🔒 Блокируем файл для конкурентного доступа
                with open(URL_FILE_PATH, "a", encoding="utf-8") as f:
                    for url in urls:
                        f.write(url + "\n")

            logging.info(f"Добавлено {len(urls)} новых URL в {URL_FILE_PATH}")
        except Exception as e:
            logging.error(f"Ошибка при записи URL в файл: {e}")

    async def increment_user_count(self, count_users: int):
        """
        🔥 Увеличивает счетчик созданных пользователей в Redis.
        """
        try:
            redis = await aioredis.from_url("redis://localhost")
            await redis.incrby(REDIS_KEY, count_users)
            await redis.close()
            logging.info(f"📈 Увеличен счетчик созданных пользователей на {count_users}.")
        except Exception as e:
            logging.error(f"Ошибка при увеличении счетчика пользователей в Redis: {e}")

    async def reset_daily_count(self):
        """
        🕛 В 1:00 ночи сбрасывает счетчик созданных пользователей в Redis.
        """
        try:
            redis = await aioredis.from_url("redis://localhost")
            await redis.set(REDIS_KEY, 0)
            await redis.close()
            logging.info("🔄 Дневной счетчик сброшен в Redis")
        except Exception as e:
            logging.error(f"Ошибка при сбросе счетчика в Redis: {e}")

    async def get_daily_count(self) -> int:
        """
        📊 Получает количество созданных пользователей за сегодня.
        """
        try:
            redis = await aioredis.from_url("redis://localhost")
            count = await redis.get(REDIS_KEY)
            await redis.close()
            return int(count) if count else 0
        except Exception as e:
            logging.error(f"Ошибка при получении счетчика из Redis: {e}")
            return 0