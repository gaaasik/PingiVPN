import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime

import redis.asyncio as redis
import aiosqlite
import pytz
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import hmac
import hashlib
import base64

from starlette.responses import HTMLResponse

from config_flask_redis import DATABASE_PATH

load_dotenv()

# Поддержка UTF-8 для консоли и файла
console_handler = logging.StreamHandler(sys.stdout)
console_handler.stream.reconfigure(encoding='utf-8')  # 👈 ключевая строка
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

file_handler = logging.FileHandler("payments.log", encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler, file_handler]
)
logger = logging.getLogger(__name__)
# Глобальная переменная Redis-клиента
redis_client: redis.Redis = None
#нужно сделать тестовый стенд и начать тестировать оплату !!!!!!

class PaymentData(BaseModel):
    user_id: int
    payment_id: str
    amount: str
    currency: str
    status: str
    payment_method_id: str
    payload_json: dict




# Lifespan через asynccontextmanager
@asynccontextmanager
async def app_lifespan(app: FastAPI):
    global redis_client
    logger.info("Инициализация приложения...")
    PASSWORD_REDIS = os.getenv('password_redis')
    # Инициализация Redis
    redis_client = redis.Redis(host="217.25.91.109", port=6379, password=PASSWORD_REDIS, decode_responses=True)
    logger.info("Redis успешно инициализирован.")
    try:
        await redis_client.ping()
        logger.info("✅ Подключение к Redis прошло успешно.")
    except Exception as e:
        logger.error(f"❌ Не удалось подключиться к Redis: {e}")
    yield  # Здесь FastAPI выполняет действия приложения

    # Закрытие Redis при завершении
    await redis_client.close()
    logger.info("Соединение с Redis закрыто.")
    logger.info("Приложение остановлено.")
# Создаем приложение FastAPI с lifespan

app = FastAPI(lifespan=app_lifespan)

# Сохранение некорректного payload в БД
async def save_invalid_payment_to_db(payment_json: dict):
    moscow_tz = pytz.timezone("Europe/Moscow")
    created_at = datetime.now(moscow_tz).strftime("%Y-%m-%d %H:%M:%S")

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO payments (user_id, payment_id, amount, currency, status, payment_method_id, created_at, updated_at, payment_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (None, None, None, None, "invalid", None, created_at, created_at, json.dumps(payment_json)))
        await db.commit()


# Сохранение платежей в БД
async def save_payment_to_db(payment_data: PaymentData):
    try:
        moscow_tz = pytz.timezone("Europe/Moscow")
        created_at = datetime.now(moscow_tz).strftime("%Y-%m-%d %H:%M:%S")

        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Проверка существующей записи
            async with db.execute("SELECT id FROM payments WHERE payment_id = ?", (payment_data.payment_id,)) as cursor:
                existing_payment = await cursor.fetchone()

            if existing_payment:
                await db.execute("""
                    UPDATE payments
                    SET status = ?, updated_at = ?, payment_json = ?
                    WHERE payment_id = ?
                """, (payment_data.status, created_at, json.dumps(payment_data.payload_json), payment_data.payment_id))
                logger.info(f"Обновлена запись о платеже с payment_id={payment_data.payment_id}")
            else:
                await db.execute("""
                    INSERT INTO payments (chat_id, payment_id, amount, currency, status, payment_method_id, created_at, updated_at, payment_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    payment_data.user_id,
                    payment_data.payment_id,
                    payment_data.amount,
                    payment_data.currency,
                    payment_data.status,
                    payment_data.payment_method_id,
                    created_at,
                    created_at,
                    json.dumps(payment_data.payload_json)
                ))
                logger.info(f"Добавлена новая запись о платеже с payment_id={payment_data.payment_id}")

            await db.commit()

    except Exception as e:
        logger.error(f"Ошибка записи платежа в базу данных: {e}")


# Вебхук для обработки платежей
@app.post("/webhook")
async def webhook(request: Request):
    logger.info("Получен webhook - начало обработки")
    try:

        # Получение тела запроса
        body = await request.body()
        # Логируем все заголовки запроса
        headers = dict(request.headers)
        # logger.info(f"Заголовки запроса: {headers}")
        # logger.info(f",,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,")
        # logger.info(f"Тело запроса: {body}")

        # # Извлечение подписи из заголовка
        # signature = request.headers.get("X-Content-HMAC-SHA256")
        # if not signature:
        #     logger.error("Подпись отсутствует в заголовках")
        #     raise HTTPException(status_code=400, detail="Missing signature")
        #
        # # Проверка подписи
        # if not verify_signature(body, signature):
        #     logger.error("Некорректная подпись")
        #     raise HTTPException(status_code=403, detail="Invalid signature")

        # Получение JSON из запроса
        payload = await request.json()

        if not payload or "event" not in payload:
            logger.error("Некорректный payload: отсутствует поле 'event'")
            raise HTTPException(status_code=400, detail="Missing or invalid payload")

        # Извлечение данных
        event_type = payload.get("event")
        payment_info = payload.get("object", {})
        payment_id = payment_info.get("id", "Нет ID")
        amount = payment_info.get("amount", {}).get("value", "Нет суммы")
        currency = payment_info.get("amount", {}).get("currency", "Нет валюты")
        user_id = payment_info.get("metadata", {}).get("user_id")
        payment_method_id = payment_info.get("payment_method", {}).get("id", "0")

        if not user_id:
            logger.error("Отсутствует user_id в метаданных платежа")
            raise HTTPException(status_code=400, detail="Missing user_id")

        logger.info(f"Получено событие: {event_type}, ID платежа: {payment_id}, сумма: {amount} {currency}, пользователь: {user_id}")

        # Формируем сообщение
        message = {
            "user_id": user_id,
            "payment_id": payment_id,
            "amount": amount,
            "currency": currency,
            "status": event_type,
            "payment_method_id": payment_method_id,
            "payload_json": payload
        }

        # # Отправляем в Redis
        # await redis_client.lpush("payment_notifications", json.dumps(message))
        # logger.info(f"Платёж {payment_id} добавлен в очередь Redis")

        #Для тестов!!
        # Отправляем в Redis
        await redis_client.lpush("payment_notifications_test", json.dumps(message))
        logger.info(f"Платёж {payment_id} добавлен в очередь Redis")

        # Сохраняем в БД
        payment_data = PaymentData(
            user_id=user_id,
            payment_id=payment_id,
            amount=amount,
            currency=currency,
            status=event_type,
            payment_method_id=payment_method_id,
            payload_json=payload
        )
        await save_payment_to_db(payment_data)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Ошибка обработки вебхука: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
        <head>
            <title>FastAPI Webhook Receiver</title>
        </head>
        <body>
            <h1>✅ FastAPI работает!</h1>
            <p>Ожидаем webhook от Юкассы на <code>/webhook</code></p>
        </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
