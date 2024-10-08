# import asyncio
# import hmac
# import hashlib
# import logging
# import os
# import sqlite3
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
# # # Настройка Redis
# # redis_host = os.getenv('REDIS_HOST', 'localhost')
# # redis_port = os.getenv('REDIS_PORT', 6379)
# # redis_password = os.getenv('REDIS_PASSWORD', None)
# # redis_queue = os.getenv('REDIS_QUEUE', 'payment_notifications')
# #
# # # Подключение к Redis
# # redis_client = redis.Redis(host=redis_host, port=redis_port, password=redis_password)
#
# def get_moscow_time():
#     """Получение текущего времени в часовом поясе Москвы."""
#     moscow_tz = pytz.timezone('Europe/Moscow')
#     return datetime.now(moscow_tz)
#
# async def update_has_paid_subscription_db(status, chat_id, aiosqlite=None):
#     """Асинхронное обновление статуса подписки пользователя в базе данных."""
#     try:
#         conn = await aiosqlite.connect(db_path)
#         await conn.execute("UPDATE users SET has_paid_subscription = ? WHERE chat_id = ?", (status, chat_id))
#         await conn.commit()
#         logger.info(f"Статус подписки пользователя {chat_id} обновлен на {status}.")
#     except Exception as e:
#         logger.error(f"Ошибка обновления статуса подписки в базе данных: {e}")
#     finally:
#         await conn.close()
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
# # Маршрут для вебхука от Юкассы
# @app.route('/webhook', methods=['POST'])
# def webhook():
#     logger.info(f"webhook получен - начинаем обработку:")
#     try:
#         # Получаем данные из запроса
#         data = request.get_data(as_text=True)
#         signature = request.headers.get('HTTP_YANDEX_SIGNATURE')
#
#         # Проверка подписи
#         if not verify_signature(data, signature):
#             return jsonify({"status": "error", "message": "Invalid signature"}), 403
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
#                 asyncio.run(update_has_paid_subscription_db(user_id, True))
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
# if __name__ == "__main__":
#     app.run(host='0.0.0.0', port=5000)
