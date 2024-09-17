import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from aiogram.types import FSInputFile

database_path_local = Path(os.getenv('database_path_local'))

class User:
    def __init__(self, chat_id, username, device=None):
        self.chat_id = chat_id
        self.username = username
        self.device = device

    @staticmethod
    def get_user_from_db(user_id):
        conn = sqlite3.connect(database_path_local)
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id, user_name, device FROM users WHERE chat_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()

        if result:
            chat_id, username, device = result
            return User(chat_id, username, device)
        return None
    @staticmethod
    def update_device(chat_id, device):
        conn = sqlite3.connect(database_path_local)
        cursor = conn.cursor()
        try:
            # Обновляем устройство пользователя по его chat_id
            cursor.execute("""
                UPDATE users
                SET device = ?
                WHERE chat_id = ?
            """, (device, chat_id))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Ошибка обновления устройства для chat_id {chat_id}: {e}")
        finally:
            conn.close()