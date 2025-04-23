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

def decrypt_json_file():
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

        # Попробуем сначала json.loads напрямую
        try:
            return json.loads(decrypted_data)
        except json.JSONDecodeError:
            logger.warning("[WARN] JSONDecodeError. Пробуем заменить кавычки и декодировать снова...")
            corrected = decrypted_data.replace("'", '"')
            return json.loads(corrected)

    except InvalidToken:
        logger.exception("[ERROR] Невалидный токен: проверь FERNET_KEY и целостность файла.")
        raise

    except Exception as e:
        logger.exception(f"[ERROR] Ошибка при расшифровке: {e}")
        raise
