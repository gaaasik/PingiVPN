import logging
import aiosqlite
from datetime import datetime
import pytz
from flask_app.config_flask_redis import DATABASE_PATH
#from flask_app.redis_utils import send_to_redis

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def initialize_db():
    """Асинхронная инициализация базы данных с использованием aiosqlite."""
    async with aiosqlite.connect(DATABASE_PATH) as connection:
        await connection.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                payment_id TEXT UNIQUE,
                amount REAL,
                currency TEXT,
                status TEXT,
                payment_method_id TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        await connection.commit()
