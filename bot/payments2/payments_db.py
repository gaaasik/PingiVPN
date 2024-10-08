# from datetime import datetime
# from pathlib import Path
# import os
# import sqlite3
# import pytz
# from dotenv import load_dotenv
#
#
# load_dotenv()
#
# # Путь к базе данных
# db_path = Path(os.getenv('database_path_local'))
#
#
# def get_moscow_time():
#     moscow_tz = pytz.timezone('Europe/Moscow')
#     return datetime.now(moscow_tz)
#
# async def init_payment_db():
#     connection = sqlite3.connect(db_path)
#     cursor = connection.cursor()
#
#     # Проверка существования таблицы
#     cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payments'")
#     table_exists = cursor.fetchone()
#
#     # Создание таблицы payments, если она не существует
#     if not table_exists:
#         cursor.execute("""
#             CREATE TABLE payments (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 user_id INTEGER,
#                 payment_id VARCHAR(255) UNIQUE,
#                 payment_method_id VARCHAR(255) DEFAULT '0',
#                 amount DECIMAL(10, 2),
#                 currency VARCHAR(10),
#                 status VARCHAR(50),
#                 created_at TIMESTAMP,
#                 updated_at TIMESTAMP
#             )
#             """)
#         print("Таблица 'payments' была успешно создана.")
#     else:
#         print("Таблица 'payments' уже существует. Пропускаем создание.")
#
#     connection.commit()
#     connection.close()
#
# async def update_has_paid_subscription_db(status, chat_id, aiosqlite=None):
#     conn = await aiosqlite.connect(db_path)
#     await conn.execute("UPDATE users SET has_paid_subscription = ? WHERE chat_id = ?", (status, chat_id))
#     print(conn)
#     await conn.commit()
#     await conn.close()
#
# # Функция для обновления информации о платеже в базе данных с московским временем
# def update_payment_status(payment_id, user_id, amount, currency, status, payment_method_id):
#     connection = sqlite3.connect(db_path)
#     cursor = connection.cursor()
#     moscow_time = get_moscow_time()
#
#     cursor.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,))
#     payment_exists = cursor.fetchone()
#
#     if payment_exists:
#         cursor.execute("""
#         UPDATE payments
#         SET status = ?, updated_at = ?
#         WHERE payment_id = ?
#         """, (status, moscow_time, payment_id))
#     else:
#         cursor.execute("""
#         INSERT INTO payments (user_id, payment_id, amount, currency, status, payment_method_id, created_at, updated_at)
#         VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#         """, (user_id, payment_id, amount, currency, status, payment_method_id, moscow_time, moscow_time))
#
#     connection.commit()
#     connection.close()