import asyncio
import json
import logging
import os

import aiofiles
import redis.asyncio as redis
import requests

from dotenv import load_dotenv
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("payments.log"),
        logging.StreamHandler()
    ],
    encoding="utf-8"
)
my_logging = logging.getLogger(__name__)

load_dotenv()

class ServerSettings:
    """Настройки сервера.response"""
    REDIS_HOST = os.getenv("ip_redis_server").strip()
    REDIS_PORT = int(os.getenv("port_redis"))
    REDIS_PASSWORD = os.getenv("password_redis").strip()
    NAME_RESULT_QUEUE = os.getenv("name_queue_result_task").strip()
    COUNTRY_SERVER_FILE = Path(__file__).resolve().parent.parent / "country_server.txt"

    # Определение IP-адреса сервера при старте
    SERVER_IP = None
    SERVER_NAME = None
    SERVER_COUNTRY = None
    SERVER_COUNT_USERS = None
    NAME_TASK_QUEUE = None
    SERVER_PUBLIC_KEY_WG = None

    @classmethod
    def get_local_ip(cls) -> str:
        """Получает публичный IP-адрес сервера."""
        try:
            response = requests.get("https://api.ipify.org", timeout=5)
            response.raise_for_status()
            server_ip = response.text.strip()
            my_logging.info(f"Публичный IP-адрес: {server_ip}")
            return server_ip
        except Exception as e:
            my_logging.error(f"Не удалось получить публичный IP: {e}")
            return None  # Если не удалось определить IP

    @classmethod
    async def load_server_data_by_ip(cls, server_ip: str):
        """Загружает имя сервера по его IP из файла."""
        try:
            my_logging.info(f"Читаем файл {cls.COUNTRY_SERVER_FILE} для IP {server_ip}")
            async with aiofiles.open(cls.COUNTRY_SERVER_FILE, mode="r", encoding="utf-8") as file:
                servers_data = json.loads(await file.read())

            for server in servers_data.get("servers", []):
                if server.get("address") == server_ip:
                    my_logging.info(f"Сервер найден: {server}")
                    cls.SERVER_NAME = server.get("name", "Unknown_Server")
                    cls.SERVER_COUNTRY = server.get("country", "Unknown")
                    cls.SERVER_COUNT_USERS = server.get("count_users", 50)
                    return True
        except FileNotFoundError:
            my_logging.warning(f"Файл {cls.COUNTRY_SERVER_FILE} не найден.")
        except json.JSONDecodeError as e:
            my_logging.error(f"Ошибка декодирования JSON: {e}")
        except Exception as e:
            my_logging.error(f"Ошибка при чтении файла {cls.COUNTRY_SERVER_FILE}: {e}")
        return False

    @classmethod
    async def check_wg_config_path(cls) -> str:
        """Определяет путь к файлу конфигурации WireGuard."""
        if Path(cls.PATH_PRIMARY_WG_JSON).exists():
            my_logging.info(f"Файл WireGuard найден: {cls.PATH_PRIMARY_WG_JSON}")
            return cls.PATH_PRIMARY_WG_JSON
        elif Path(cls.ALTERNATE_WG_CONFIG_PATH).exists():
            my_logging.info(f"Файл WireGuard найден: {cls.ALTERNATE_WG_CONFIG_PATH}")
            return cls.ALTERNATE_WG_CONFIG_PATH
        else:
            my_logging.warning("Файл WireGuard не найден.")
            return None

    @classmethod
    async def check_vless_database(cls) -> bool:
        """Проверяет наличие базы данных VLESS (x-ui)."""
        if Path(cls.PATH_DATABASE_X_UI).exists():
            my_logging.info(f"База данных VLESS найдена: {cls.PATH_DATABASE_X_UI}")
            return True
        else:
            my_logging.warning("База данных VLESS не найдена.")
            return False

    @classmethod
    async def initialize(cls):
        """Инициализирует IP, имя сервера и очередь Redis."""
        #Поиск правильного пути файла
        cls.PATH_PRIMARY_WG_JSON = await cls.check_wg_config_path()

        # Проверка наличия базы данных VLESS
        cls.VLESS_DB_FOUND = await cls.check_vless_database()
        cls.SERVER_PUBLIC_KEY_WG = await cls.get_server_public_key()

        # Если не найдено ни WireGuard, ни VLESS, останавливаем программу
        if not cls.PATH_PRIMARY_WG_JSON and not cls.VLESS_DB_FOUND:
            my_logging.error("Не найден ни WireGuard, ни база данных VLESS. Завершаю работу.")
            exit(1)

        cls.SERVER_IP = cls.get_local_ip()
        if not cls.SERVER_IP:
            my_logging.error("Не удалось определить IP сервера. Завершаю работу.")
            exit(1)

        await cls.load_server_data_by_ip(cls.SERVER_IP)
        if cls.SERVER_NAME == "Unknown_Server":
            my_logging.error("Имя сервера не найдено. Завершаю работу.")
            exit(1)
        if cls.SERVER_NAME == "Unknown_Server":
            my_logging.error("Имя сервера не найдено. Завершаю работу.")
            exit(1)

        cls.NAME_TASK_QUEUE = f"queue_task_{cls.SERVER_NAME}"  # Если сервер найден, создаем очередь
        my_logging.info(f"Определен сервер: {cls.SERVER_NAME}")


    @classmethod
    async def get_redis_client(cls):
        return redis.Redis(
            host=cls.REDIS_HOST,
            port=cls.REDIS_PORT,
            password=cls.REDIS_PASSWORD,
            decode_responses=True,
        )

    @classmethod
    async def get_server_public_key(cls) -> str:
        """Получает публичный ключ сервера WireGuard."""
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "exec", "wg-easy", "wg", "show", "wg0", "public-key",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                my_logging.info(f"достали public-key = {stdout.decode().strip()}")
                return stdout.decode().strip()
            else:
                my_logging.info(f"Не достали public-key = {stdout.decode().strip()}")
                raise RuntimeError(stderr.decode().strip())

        except Exception as e:
            my_logging.error(f"Не удалось получить публичный ключ сервера WG: {e}")
            return ""


