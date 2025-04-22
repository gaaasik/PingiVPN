import base64
import json
from cryptography.fernet import Fernet
from work_user_api.config import FERNET_KEY, ENCRYPTED_JSON_PATH

def decrypt_json_file() -> dict:
    with open(ENCRYPTED_JSON_PATH, "rb") as f:
        encrypted_data = f.read()
    fernet = Fernet(FERNET_KEY.encode())
    decrypted = fernet.decrypt(encrypted_data)
    return json.loads(decrypted)