import json
import logging
import os
from cryptography.fernet import Fernet, InvalidToken
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

FERNET_KEY = os.getenv("FERNET_KEY")
ENCRYPTED_FILE = Path(__file__).parent / "secure" / "servers_encrypted.json"

_server_cache = None  # это глобальная переменная


def decrypt_json_file():
    global _server_cache

    if _server_cache is not None:
        return _server_cache

    logger.info("[INFO] Начинаем расшифровку JSON-файла серверов...")

    if not FERNET_KEY:
        logger.error("[ERROR] FERNET_KEY не найден в .env файле!")
        raise ValueError("FERNET_KEY не установлен")

    try:
        with open(ENCRYPTED_FILE, "r", encoding="utf-8") as file:
            encrypted_json = json.load(file)
            token = encrypted_json["servers"]

        fernet = Fernet(FERNET_KEY)
        decrypted_data = fernet.decrypt(token.encode("utf-8")).decode("utf-8")

        try:
            _server_cache = json.loads(decrypted_data)
        except json.JSONDecodeError:
            logger.warning("[WARN] JSONDecodeError. Пробуем заменить кавычки и декодировать снова...")
            corrected = decrypted_data.replace("'", '"')
            _server_cache = json.loads(corrected)

        return _server_cache

    except InvalidToken:
        logger.exception("[ERROR] Невалидный токен: проверь FERNET_KEY и целостность файла.")
        raise

    except Exception as e:
        logger.exception(f"[ERROR] Ошибка при расшифровке: {e}")
        raise


def get_server_credentials_by_ip(server_ip: str):
    """
    Возвращает данные для подключения к серверу по IP:
    xui_url, login и password.

    Если сервер не найден — выбрасывает ValueError.
    """
    servers_data = decrypt_json_file()  # Здесь теперь будет список, а не словарь

    for s in servers_data:  # без .get("servers")
        if s.get("address") == server_ip:
            return {
                "xui_url": s.get("3X_UI", "").strip(),
                "login": s["passwords"]["login"],
                "password": s["passwords"]["password"]
            }

    # Если не нашли сервер — кидаем исключение
    raise ValueError(f"Сервер с IP {server_ip} не найден в зашифрованном файле.")


def clear_server_cache():
    """Очистить кэш, если вдруг понадобится пересчитать."""
    global _server_cache
    _server_cache = None
