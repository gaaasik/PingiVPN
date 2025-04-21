from json_crypto_tool.encryptor import decrypt_data
from json_crypto_tool.loader import load_json
from work_user_api.config import ENCRYPTED_SERVERS_FILE

def load_decrypted_servers():
    encrypted = load_json(ENCRYPTED_SERVERS_FILE)
    return decrypt_data(encrypted)