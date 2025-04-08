import json
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Глобальная переменная для хранения данных серверов aioredis
country_server_data = None
# Загружаем данные один раз


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
logger = logging.getLogger(__name__)


async def load_server_data(country_server_path: str):
    global country_server_data
    try:
        # Преобразуем строку пути в объект Path
        path = Path(country_server_path)
        if not path.exists():
            raise FileNotFoundError(f"Файл {path} не найден.")

        with path.open(mode="r", encoding="utf-8") as file:
            logging.info("Данные серверов успешно загружены.")
            country_server_data = json.load(file)

    except Exception as e:
        logging.error(f"Ошибка при загрузке данных серверов: {e}")
        raise


async def get_json_country_server_data():
    global country_server_data
    if country_server_data is None:
        country_server_data = "Unknown_Server"
        raise ValueError("Данные country_server_data еще не загружены.")
    return country_server_data


async def get_name_server_by_ip(server_ip: str) -> str:
    """Получает имя сервера по его IP."""
    global country_server_data
    if country_server_data is None:
        raise ValueError("Данные country_server_data еще не загружены.")

    for server in country_server_data.get("servers", []):
        if server.get("address") == server_ip:
            return server.get("name", "Unknown_Server")
    return "Unknown_Server"  # Если сервер не найден

async def get_protocol_server_by_ip(server_ip: str) -> str:
    """Получает имя сервера по его IP."""
    global country_server_data
    if country_server_data is None:
        raise ValueError("Данные country_server_data еще не загружены.")

    for server in country_server_data.get("servers", []):
        if server.get("address") == server_ip:
            return server.get("name_protocol", None)
    return None  # Если сервер не найден


async def get_country_server_by_ip(server_ip: str) -> str:
    """Получает имя сервера по его IP."""
    global country_server_data
    if country_server_data is None:
        raise ValueError("Данные country_server_data еще не загружены.")

    for server in country_server_data.get("servers", []):
        if server.get("address") == server_ip:
            return server.get("country", "Unknown")
    return "Unknown_Server"  # Если сервер не найден


async def get_all_non_test_server_ips() -> list[str]:
    """
    Возвращает список IP всех серверов, у которых в имени нет 'test'.
    """
    global country_server_data
    if country_server_data is None:
        raise ValueError("Данные country_server_data еще не загружены.")

    non_test_ips = []
    for server in country_server_data.get("servers", []):
        name = server.get("name", "")
        ip = server.get("address", "")
        if "test" not in name.lower():
            non_test_ips.append(ip)
    return non_test_ips