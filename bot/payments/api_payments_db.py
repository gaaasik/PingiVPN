


from pathlib import Path
import os
import sqlite3
from datetime import datetime
import pytz
from dotenv import load_dotenv


load_dotenv()

# Путь к базе данных
db_path = Path(os.getenv('database_path_local'))

moscow_tz = pytz.timezone('Europe/Moscow')

# Функция для получения текущего времени по Москве
def get_moscow_time():
    return datetime.now(moscow_tz)

# Функция для инициализации базы данных


# Функция для обновления информации о платеже в базе данных с московским временем
def update_payment_status(payment_id, user_id, amount, currency, status, payment_method_id):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    moscow_time = get_moscow_time()

    cursor.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,))
    payment_exists = cursor.fetchone()

    if payment_exists:
        cursor.execute("""
        UPDATE payments
        SET status = ?, updated_at = ?
        WHERE payment_id = ?
        """, (status, moscow_time, payment_id))
    else:
        cursor.execute("""
        INSERT INTO payments (user_id, payment_id, amount, currency, status, payment_method_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, payment_id, amount, currency, status, payment_method_id, moscow_time, moscow_time))

    connection.commit()
    connection.close()


# Функция для проверки подписки
def check_subscription(user_id):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute("""
    SELECT * FROM payments 
    WHERE user_id = ? AND status = 'payment.succeeded'
    """, (user_id,))
    subscription_exists = cursor.fetchone()
    connection.close()
    return subscription_exists is not None





# Функция для удаления записей с указанным user_id
def delete_payments_by_user(user_id):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute("DELETE FROM payments WHERE user_id = ?", (user_id,))
    connection.commit()
    connection.close()
    print(f"Все записи с user_id = {user_id} удалены.")





