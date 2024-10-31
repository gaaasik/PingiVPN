import asyncio
import json
from datetime import datetime
import aiosqlite
import pytz
import redis
from flask import Flask, jsonify, request
from flask_app.all_utils_flask_db import initialize_db, logger#, update_payment_status

app = Flask(__name__)
redis_client = redis.Redis(host='localhost', port=6379)
# Сохраняем некорректный payload в таблицу payments
async def save_invalid_payment_to_db(payment_json):
    moscow_tz = pytz.timezone("Europe/Moscow")
    created_at = datetime.now(moscow_tz).strftime("%Y-%m-%d %H:%M:%S")

    async with aiosqlite.connect("payments.db") as db:
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

    async with aiosqlite.connect("payments.db") as db:
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
            "payment_method_id": payment_method_id
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

