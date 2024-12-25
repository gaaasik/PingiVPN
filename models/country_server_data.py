import json
import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Глобальная переменная для хранения данных серверов
country_server_data = None
# Загружаем данные один раз

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

async def get_country_server_data():
    global country_server_data
    if country_server_data is None:
        raise ValueError("Данные country_server_data еще не загружены.")
    return country_server_data