from pathlib import Path
import os
import sqlite3
import pytz
from dotenv import load_dotenv


load_dotenv()

# Путь к базе данных
db_path = Path(os.getenv('database_path_local'))

moscow_tz = pytz.timezone('Europe/Moscow')


async def init_payment_db():
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    # Проверка существования таблицы
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payments'")
    table_exists = cursor.fetchone()

    # Создание таблицы payments, если она не существует
    if not table_exists:
        cursor.execute("""
            CREATE TABLE payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                payment_id VARCHAR(255) UNIQUE,
                payment_method_id VARCHAR(255) DEFAULT '0',
                amount DECIMAL(10, 2),
                currency VARCHAR(10),
                status VARCHAR(50),
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
            """)
        print("Таблица 'payments' была успешно создана.")
    else:
        print("Таблица 'payments' уже существует. Пропускаем создание.")

    connection.commit()
    connection.close()

async def update_has_paid_subscription_db(status, chat_id, aiosqlite=None):
    conn = await aiosqlite.connect(db_path)
    await conn.execute("UPDATE users SET has_paid_subscription = ? WHERE chat_id = ?", (status, chat_id))
    print(conn)
    await conn.commit()
    await conn.close()