import asyncio
import json
import logging
from datetime import datetime

import aioredis
import aiosqlite
import pytz
from flask import Flask, jsonify, request
from flask_app.all_utils_flask_db import initialize_db  # , update_payment_status
from models.UserCl import database_path_local

# Создание приложения Flask
app = Flask(__name__)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("payments.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Redis-клиент
redis_client = None


# Асинхронная инициализация Redis
@app.before_first_request
async def init_redis():
    global redis_client
    redis_client = await aioredis.from_url("redis://localhost:6379", decode_responses=True)
    logger.info("Redis успешно инициализирован.")


# Сохранение некорректного payload в таблицу payments
async def save_invalid_payment_to_db(payment_json):
    moscow_tz = pytz.timezone("Europe/Moscow")
    created_at = datetime.now(moscow_tz).strftime("%Y-%m-%d %H:%M:%S")

    async with aiosqlite.connect(database_path_local) as db:
        await db.execute("""
            INSERT INTO payments (user_id, payment_id, amount, currency, status, payment_method_id, created_at, updated_at, payment_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (None, None, None, None, "invalid", None, created_at, created_at, json.dumps(payment_json)))
        await db.commit()


# Функция для записи платежей в базу данных
async def save_payment_to_db(user_id, payment_id, amount, currency, status, payment_method_id, payment_json):
    try:
        moscow_tz = pytz.timezone("Europe/Moscow")
        created_at = datetime.now(moscow_tz).strftime("%Y-%m-%d %H:%M:%S")
        updated_at = created_at

        async with aiosqlite.connect(database_path_local) as db:
            # Проверка наличия записи по payment_id
            async with db.execute("SELECT id FROM payments WHERE payment_id = ?", (payment_id,)) as cursor:
                existing_payment = await cursor.fetchone()

            if existing_payment:
                await db.execute("""
                    UPDATE payments
                    SET status = ?, updated_at = ?, payment_json = ?
                    WHERE payment_id = ?
                """, (status, updated_at, json.dumps(payment_json), payment_id))
                logger.info(f"Обновлена запись о платеже с payment_id={payment_id}")
            else:
                await db.execute("""
                    INSERT INTO payments (chat_id, payment_id, amount, currency, status, payment_method_id, created_at, updated_at, payment_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, payment_id, amount, currency, status, payment_method_id, created_at, updated_at,
                      json.dumps(payment_json)))
                logger.info(f"Добавлена новая запись о платеже с payment_id={payment_id}")

            await db.commit()

    except Exception as e:
        logger.error(f"Ошибка записи платежа в базу данных: {e}")


# Вебхук для обработки платежей
@app.route('/webhook', methods=['POST'])
async def webhook():
    logger.info("Получен webhook - начало обработки")

    try:
        # Получаем данные из вебхука
        payload = request.json
        if not payload or 'event' not in payload:
            logger.error("Некорректный payload: отсутствует поле 'event'")
            return jsonify({"status": "error", "message": "Missing or invalid payload"}), 400

        # Извлекаем информацию из payload
        event_type = payload.get('event')
        payment_info = payload.get('object', {})
        payment_id = payment_info.get('id', 'Нет ID')
        amount = payment_info.get('amount', {}).get('value', 'Нет суммы')
        currency = payment_info.get('amount', {}).get('currency', 'Нет валюты')
        user_id = payment_info.get('metadata', {}).get('user_id', None)
        payment_method_id = payment_info.get('payment_method', {}).get('id', '0')

        if not user_id:
            logger.error("Отсутствует user_id в метаданных платежа")
            return jsonify({"status": "error", "message": "Missing user_id"}), 400

        logger.info(f"Получено событие: {event_type}, ID платежа: {payment_id}, сумма: {amount} {currency}, пользователь: {user_id}")

        # Формируем сообщение для Redis
        message = {
            "user_id": user_id,
            "payment_id": payment_id,
            "amount": amount,
            "currency": currency,
            "status": event_type,
            "payment_method_id": payment_method_id,
            "payload_json": payload
        }

        # Отправляем сообщение в Redis
        await redis_client.lpush('payment_notifications', json.dumps(message))
        logger.info(f"Платёж {payment_id} добавлен в очередь Redis")

        # Сохраняем данные о платеже в базу
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
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=5000)


# import asyncio
# import json
# import logging
# from datetime import datetime
#
# import aioredis
# import aiosqlite
# import pytz
# import redis
# from flask import Flask, jsonify, request
# from flask_app.all_utils_flask_db import initialize_db  #, update_payment_status
# from models.UserCl import database_path_local
#
# app = Flask(__name__)
#
# # Настройка логирования
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler("payments.log"),
#         logging.StreamHandler()
#     ]
# )
# logger = logging.getLogger(__name__)
#
# redis_client = aioredis.Redis(host='localhost', port=6379)
#
#
# # Сохраняем некорректный payload в таблицу payments
# async def save_invalid_payment_to_db(payment_json):
#     moscow_tz = pytz.timezone("Europe/Moscow")
#     created_at = datetime.now(moscow_tz).strftime("%Y-%m-%d %H:%M:%S")
#
#     async with aiosqlite.connect(database_path_local) as db:
#         await db.execute("""
#             INSERT INTO payments (user_id, payment_id, amount, currency, status, payment_method_id, created_at, updated_at, payment_json)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """, (None, None, None, None, "invalid", None, created_at, created_at, json.dumps(payment_json)))
#         await db.commit()
#
#
# # Функция для записи платежей в базу данных
# async def save_payment_to_db(user_id, payment_id, amount, currency, status, payment_method_id, payment_json):
#     try:
#         # Московское время
#         moscow_tz = pytz.timezone("Europe/Moscow")
#         created_at = datetime.now(moscow_tz).strftime("%Y-%m-%d %H:%M:%S")
#         updated_at = created_at
#
#         async with aiosqlite.connect(database_path_local) as db:
#             # Проверяем наличие записи по payment_id
#             async with db.execute("SELECT id FROM payments WHERE payment_id = ?", (payment_id,)) as cursor:
#                 existing_payment = await cursor.fetchone()
#
#             if existing_payment:
#                 # Если запись существует, обновляем её
#                 await db.execute("""
#                     UPDATE payments
#                     SET status = ?, updated_at = ?, payment_json = ?
#                     WHERE payment_id = ?
#                 """, (status, updated_at, json.dumps(payment_json), payment_id))
#                 logger.info(f"Обновлена запись о платеже с payment_id={payment_id}")
#             else:
#                 # Если записи нет, добавляем новую
#                 await db.execute("""
#                     INSERT INTO payments (chat_id, payment_id, amount, currency, status, payment_method_id, created_at, updated_at, payment_json)
#                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
#                 """, (user_id, payment_id, amount, currency, status, payment_method_id, created_at, updated_at,
#                       json.dumps(payment_json)))
#                 logger.info(f"Добавлена новая запись о платеже с payment_id={payment_id}")
#
#             await db.commit()
#
#     except Exception as e:
#         logger.error(f"Ошибка записи платежа в базу данных: {e}")
#
# # Вебхук для обработки платежей
# @app.route('/webhook', methods=['POST'])
# async def webhook():
#     logger.info("Получен webhook - начало обработки")
#
#     try:
#         # Получаем данные из вебхука
#         payload = request.json
#         if not payload or 'event' not in payload:
#             logger.error("Некорректный payload: отсутствует поле 'event'")
#             return jsonify({"status": "error", "message": "Missing or invalid payload"}), 400
#
#         # Извлекаем информацию из payload
#         event_type = payload.get('event')
#         payment_info = payload.get('object', {})
#         payment_id = payment_info.get('id', 'Нет ID')
#         amount = payment_info.get('amount', {}).get('value', 'Нет суммы')
#         currency = payment_info.get('amount', {}).get('currency', 'Нет валюты')
#         user_id = payment_info.get('metadata', {}).get('user_id', None)
#         payment_method_id = payment_info.get('payment_method', {}).get('id', '0')
#
#         if not user_id:
#             logger.error("Отсутствует user_id в метаданных платежа")
#             return jsonify({"status": "error", "message": "Missing user_id"}), 400
#
#         logger.info(f"Получено событие: {event_type}, ID платежа: {payment_id}, сумма: {amount} {currency}, пользователь: {user_id}")
#
#         # Формируем сообщение для Redis
#         message = {
#             "user_id": user_id,
#             "payment_id": payment_id,
#             "amount": amount,
#             "currency": currency,
#             "status": event_type,
#             "payment_method_id": payment_method_id,
#             "payload_json": payload
#         }
#
#         # Отправляем сообщение в Redis
#         await redis_client.lpush('payment_notifications', json.dumps(message))
#         logger.info(f"Платёж {payment_id} добавлен в очередь Redis")
#
#         # Сохраняем данные о платеже в базу
#         await save_payment_to_db(
#             user_id=user_id,
#             payment_id=payment_id,
#             amount=amount,
#             currency=currency,
#             status=event_type,
#             payment_method_id=payment_method_id,
#             payment_json=payment_info
#         )
#
#         return jsonify({"status": "ok"}), 200
#
#     except Exception as e:
#         logger.error(f"Ошибка обработки вебхука: {e}")
#         return jsonify({"status": "error", "message": "Internal server error"}), 500
#
# @app.route('/', methods=['GET'])
# def home():
#     return "Hello, this is Flask application!", 200
#
#
# if __name__ == "__main__":
#     app.run(host='0.0.0.0', port=5000)
