import asyncio
import json
from datetime import datetime
import aiosqlite
import pytz
import redis
from flask import Flask, jsonify, request
from flask_app.all_utils_flask_db import initialize_db, logger#, update_payment_status
from models.UserCl import database_path_local

app = Flask(__name__)
redis_client = redis.Redis(host='localhost', port=6379)
# Сохраняем некорректный payload в таблицу payments
async def save_invalid_payment_to_db(payment_json):
    moscow_tz = pytz.timezone("Europe/Moscow")
    created_at = datetime.now(moscow_tz).strftime("%Y-%m-%d %H:%M:%S")

    async with aiosqlite.connect(database_path_local) as db:
        await db.execute("""
            INSERT INTO payments (user_id, payment_id, amount, currency, status, payment_method_id, created_at, updated_at, payment_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (None, None, None, None, "invalid", None, created_at, created_at, json.dumps(payment_json)))
        await db.commit()

async def save_payment_to_db(user_id, payment_id, amount, currency, status, payment_method_id, payment_json):
    # Определяем московский часовой пояс
    moscow_tz = pytz.timezone("Europe/Moscow")

    # Время создания и обновления записи в московском времени
    created_at = datetime.now(moscow_tz).strftime("%Y-%m-%d %H:%M:%S")
    updated_at = created_at

    async with aiosqlite.connect(database_path_local) as db:
        await db.execute("""
            INSERT INTO payments (user_id, payment_id, amount, currency, status, payment_method_id, created_at, updated_at, payment_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, payment_id, amount, currency, status, payment_method_id, created_at, updated_at, json.dumps(payment_json)))
        await db.commit()

@app.route('/webhook', methods=['POST'])
async def webhook():
    logger.info("webhook получен - начинаем обработку:")

    try:
        # Получаем данные из запроса
        payload = request.json
        if not payload or 'event' not in payload:
            await save_invalid_payment_to_db(payload)
            return jsonify({"status": "error", "message": "Missing or invalid payload"}), 400

        event_type = payload.get('event')
        payment_info = payload.get('object', {})
        payment_id = payment_info.get('id', 'Нет ID')
        amount = payment_info.get('amount', {}).get('value', 'Нет суммы')
        currency = payment_info.get('amount', {}).get('currency', 'Нет валюты')
        user_id = payment_info.get('metadata', {}).get('user_id', None)
        payment_method_id = payment_info.get('payment_method', {}).get('id', '0')
        print(payload)
        if not user_id:
            logger.error("Отсутствует user_id в метаданных платежа")
            return jsonify({"status": "error", "message": "Missing user_id"}), 400

            # Логирование информации о платеже
        logger.info(
            f"Получено событие: {event_type}, ID платежа: {payment_id}, сумма: {amount} {currency}, пользователь: {user_id}")

        # Формирование сообщения для отправки в Redis
        message = {
            "user_id": user_id,
            "payment_id": payment_id,
            "amount": amount,
            "currency": currency,
            "status": event_type,
            "payment_method_id": payment_method_id,
            "payload_json": payload
        }

        # Отправляем информацию о платеже в Redis-очередь
        await redis_client.lpush('payment_notifications', json.dumps(message))
        logger.info(f"Информация о платеже {payment_id} добавлена в очередь Redis")
        # Сохранение данных о платеже в базу данных
        await save_payment_to_db(
            user_id=user_id,
            payment_id=payment_id,
            amount=amount,
            currency=currency,
            status=event_type,
            payment_method_id=payment_method_id,
            payment_json=payment_info
        )
        return jsonify({"status": "ok"}), 200


    except Exception as e:
        logger.error(f"Ошибка обработки вебхука: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/', methods=['GET'])
def home():
    return "Hello, this is Flask application!", 200

if __name__ == "__main__":

    app.run(host='0.0.0.0', port=5000)



 # # Обработка событий
        # if event_type == 'payment.succeeded':
        #     logger.info(
        #         f"Оплата успешна! ID платежа: {payment_id}, Сумма: {amount} {currency}, Пользователь: {user_id}")
        #     asyncio.run(
        #         update_payment_status(payment_id, user_id, amount, currency, 'payment.succeeded', payment_method_id))
        #     # Отправка уведомления через Redis или другой метод
        #     return jsonify({"status": "ok"}), 200
        #
        # elif event_type == 'payment.waiting_for_capture':
        #     logger.info(
        #         f"Платеж ожидает подтверждения. ID платежа: {payment_id}, Сумма: {amount} {currency}, Пользователь: {user_id}")
        #     asyncio.run(update_payment_status(payment_id, user_id, amount, currency, 'payment.waiting_for_capture',
        #                                       payment_method_id))
        #     return jsonify({"status": "ok"}), 200
        #
        # elif event_type == 'payment.canceled':
        #     logger.info(
        #         f"Платеж отменен. ID платежа: {payment_id}, Сумма: {amount} {currency}, Пользователь: {user_id}")
        #     asyncio.run(
        #         update_payment_status(payment_id, user_id, amount, currency, 'payment.canceled', payment_method_id))
        #     return jsonify({"status": "ok"}), 200
        #
        # elif event_type == 'refund.succeeded':
        #     logger.info(
        #         f"Возврат выполнен успешно. ID возврата: {payment_id}, Сумма: {amount} {currency}, Пользователь: {user_id}")
        #     asyncio.run(
        #         update_payment_status(payment_id, user_id, amount, currency, 'refund.succeeded', payment_method_id))
        #     return jsonify({"status": "ok"}), 200
        #
        # else:
        #     logger.warning(f"Неизвестное событие: {event_type}")
        #     return jsonify({"status": "error", "message": "Unknown event"}), 400
# import asyncio





# import hmac
# import hashlib
# import logging
# import os
# import sqlite3
#
# import aiosqlite
# import redis
# from datetime import datetime
# from pathlib import Path
# import pytz
# from dotenv import load_dotenv
# from flask import Flask, request, jsonify
# from yookassa import Configuration, Payment
#
# # Инициализация Flask
# app = Flask(__name__)
#
# # Инициализация логирования
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)
#
# # Загрузка переменных окружения из .env файла
# load_dotenv()
#
# # Путь к базе данных
# db_path = Path(os.getenv('database_path_local'))
#
# # Настройка API Юкассы
# shop_account_id = os.getenv('SHOPID')  # Ваш shopId
# SECRET_KEY = os.getenv('API_KEY')  # Ваш секретный ключ API
#
# if not SECRET_KEY:
#     logger.error("SECRET_KEY не загружен. Проверьте переменные окружения и наличие API_KEY в .env файле.")
#
# # # Настройка Redis
# # redis_host = os.getenv('REDIS_HOST', 'localhost')
# # redis_port = os.getenv('REDIS_PORT', 6379)
# # redis_password = os.getenv('REDIS_PASSWORD', None)
# # redis_queue = os.getenv('REDIS_QUEUE', 'payment_notifications')
# #
# # # Подключение к Redis
# # redis_client = redis.Redis(host=redis_host, port=redis_port, password=redis_password)
# def initialize_db():
#     connection = sqlite3.connect(db_path)
#     cursor = connection.cursor()
#     cursor.execute('''
#         CREATE TABLE IF NOT EXISTS payments (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             user_id TEXT,
#             payment_id TEXT,
#             amount REAL,
#             currency TEXT,
#             status TEXT,
#             payment_method_id TEXT,
#             created_at TEXT,
#             updated_at TEXT
#         )
#     ''')
#     connection.commit()
#     connection.close()
#
#
#
# def get_moscow_time():
#     """Получение текущего времени в часовом поясе Москвы."""
#     moscow_tz = pytz.timezone('Europe/Moscow')
#     return datetime.now(moscow_tz)
#
# async def update_has_paid_subscription_db(status, chat_id):
#     """Асинхронное обновление статуса подписки пользователя в базе данных."""
#     conn = None
#     try:
#         conn = await aiosqlite.connect(db_path)
#         await conn.execute("UPDATE users SET has_paid_subscription = ? WHERE chat_id = ?", (status, chat_id))
#         await conn.commit()
#         logger.info(f"Статус подписки пользователя {chat_id} обновлен на {status}.")
#         logger.info(f"Статус подписки пользователя {chat_id} обновлен на {status}.")
#     except Exception as e:
#         logger.error(f"Ошибка обновления статуса подписки в базе данных: {e}")
#     finally:
#         await conn.close()
#
# def ensure_payments_table_exists():
#     """
#     Функция для проверки существования таблицы payments и ее создания при необходимости.
#     """
#     try:
#         connection = sqlite3.connect(db_path)
#         cursor = connection.cursor()
#
#         # Проверка наличия таблицы payments
#         cursor.execute("""
#             SELECT name FROM sqlite_master WHERE type='table' AND name='payments';
#         """)
#         table_exists = cursor.fetchone()
#
#         # Если таблицы нет, создаем ее
#         if not table_exists:
#             cursor.execute('''
#                 CREATE TABLE payments (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     user_id TEXT,
#                     payment_id TEXT UNIQUE,
#                     amount REAL,
#                     currency TEXT,
#                     status TEXT,
#                     payment_method_id TEXT,
#                     created_at TEXT,
#                     updated_at TEXT
#                 )
#             ''')
#             connection.commit()
#             logger.info("Таблица payments создана.")
#         else:
#             logger.info("Таблица payments уже существует.")
#
#     except Exception as e:
#         logger.error(f"Ошибка при проверке или создании таблицы payments: {e}")
#     finally:
#         connection.close()
#
#
# def add_column_to_payments(column_name, column_type="TEXT"):
#     """
#     Функция для добавления нового столбца в таблицу payments.
#     :param column_name: Имя нового столбца.
#     :param column_type: Тип данных столбца (по умолчанию TEXT).
#     """
#     try:
#         connection = sqlite3.connect(db_path)
#         cursor = connection.cursor()
#         # Создаем запрос для добавления столбца
#         query = f"ALTER TABLE payments ADD COLUMN {column_name} {column_type}"
#         cursor.execute(query)
#         connection.commit()
#         logger.info(f"Столбец {column_name} типа {column_type} успешно добавлен в таблицу payments.")
#     except sqlite3.OperationalError as e:
#         logger.error(f"Ошибка при добавлении столбца {column_name}: {e}")
#     finally:
#         connection.close()
#
#
#
# async def verify_signature(data, signature):
#     if not SECRET_KEY or not signature:
#         logger.error("Секретный ключ или подпись не могут быть пустыми.")
#         return False
#
#     try:
#         # Проверка HMAC подписи с использованием секретного ключа и данных запроса
#         hash_digest = hmac.new(SECRET_KEY.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).hexdigest()
#         is_valid = hmac.compare_digest(hash_digest, signature)
#         if not is_valid:
#             logger.warning("Получена недействительная подпись вебхука.")
#         return is_valid
#     except Exception as e:
#         logger.error(f"Ошибка при проверке подписи: {e}")
#         return False
#
#
# async def update_payment_status(payment_id, user_id, amount, currency, status, payment_method_id):
#     """Асинхронное обновление статуса платежа в базе данных."""
#     try:
#         connection = sqlite3.connect(db_path)
#         cursor = connection.cursor()
#         moscow_time = get_moscow_time()
#
#         cursor.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,))
#         payment_exists = cursor.fetchone()
#
#         if payment_exists:
#             cursor.execute("""
#             UPDATE payments
#             SET status = ?, updated_at = ?
#             WHERE payment_id = ?
#             """, (status, moscow_time, payment_id))
#             logger.info(f"Обновлен статус платежа {payment_id}: {status}")
#         else:
#             cursor.execute("""
#             INSERT INTO payments (user_id, payment_id, amount, currency, status, payment_method_id, created_at, updated_at)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#             """, (user_id, payment_id, amount, currency, status, payment_method_id, moscow_time, moscow_time))
#             logger.info(f"Добавлен новый платеж: ID {payment_id}, пользователь {user_id}, сумма {amount} {currency}.")
#
#         connection.commit()
#     except Exception as e:
#         logger.error(f"Ошибка обновления информации о платеже в базе данных: {e}")
#     finally:
#         connection.close()
#
#
# def verify_signature(data, signature):
#     """Проверка подписи HMAC для безопасности вебхуков."""
#     try:
#         hash_digest = hmac.new(SECRET_KEY.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).hexdigest()
#         is_valid = hmac.compare_digest(hash_digest, signature)
#         if not is_valid:
#             logger.warning("Получена недействительная подпись вебхука.")
#         return is_valid
#     except Exception as e:
#         logger.error(f"Ошибка при проверке подписи: {e}")
#         return False
#
# # def send_to_redis(queue, message):
# #     """Добавление сообщения в очередь Redis."""
# #     try:
# #         redis_client.lpush(queue, message)
# #         logger.info(f"Сообщение добавлено в очередь {queue}: {message}")
# #     except Exception as e:
# #         logger.error(f"Ошибка отправки сообщения в Redis: {e}")
#
#
# # Маршрут для вебхука от Юкассы
# @app.route('/webhook', methods=['POST'])
# def webhook():
#     logger.info(f"webhook получен - начинаем обработку:")
#
#     try:
#         # Получаем данные из запроса
#         data = request.get_data(as_text=True)
#         signature = request.headers.get('HTTP_YANDEX_SIGNATURE')
#         if not signature:
#             logger.error("Подпись отсутствует в заголовках запроса.")
#             print("но нам пофиг")
#             #return jsonify({"status": "error", "message": "Missing signature"}), 400
#
#
#         # # Проверка подписи
#         # if not verify_signature(data, signature):
#         #     logger.error("Подпись отсутствует в заголовках запроса 2 . но нам пофиг 2")
#         #     return jsonify({"status": "error", "message": "Invalid signature"}), 403
#
#         # Обработка данных вебхука
#         data = request.json
#         if data and 'event' in data:
#             event_type = data['event']
#             logger.info(f"Получено событие: {event_type}")
#
#             if event_type == 'payment.succeeded':
#                 payment_info = data.get('object', {})
#                 payment_id = payment_info.get('id', 'Нет ID')
#                 amount = payment_info.get('amount', {}).get('value', 'Нет суммы')
#                 currency = payment_info.get('amount', {}).get('currency', 'Нет валюты')
#                 user_id = payment_info.get('metadata', {}).get('user_id', None)
#                 payment_method_id = payment_info.get('payment_method', {}).get('id', '0')
#
#                 # Логирование успешного платежа
#                 logger.info(f"Оплата успешна! ID платежа: {payment_id}, Сумма: {amount} {currency}, Пользователь: {user_id}")
#
#                 # Обновление информации о платеже в базе данных
#                 asyncio.run(update_payment_status(payment_id, user_id, amount, currency, event_type, payment_method_id))
#                 asyncio.run(update_has_paid_subscription_db(True, user_id))
#
#                 # Отправка информации о платеже в Redis для дальнейшей обработки
#                 message = {
#                     "user_id": user_id,
#                     "payment_id": payment_id,
#                     "amount": amount,
#                     "currency": currency
#                 }
#                 #send_to_redis(redis_queue, str(message))
#                 print(str(message))
#                 return jsonify({"status": "ok"}), 200
#
#             return jsonify({"status": "error", "message": "Unknown event"}), 400
#
#     except Exception as e:
#         logger.error(f"Ошибка обработки вебхука: {e}")
#         return jsonify({"status": "error", "message": "Internal server error"}), 500
#
#
# @app.route('/', methods=['GET'])
# def home():
#     return "Hello, this is Flask application!", 200
#
# if __name__ == "__main__":
#     initialize_db()
#     # Пример использования:
#     add_column_to_payments("new_column_name")
#     # Вызов функции для проверки и создания таблицы при запуске приложения
#     ensure_payments_table_exists()
#     app.run(host='0.0.0.0', port=5000)
