from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

FERNET_KEY = os.getenv("FERNET_KEY")  # должен быть 32 байта base64
ENCRYPTED_JSON_PATH = Path(__file__).parent / "secure" / "servers_encrypted.json"