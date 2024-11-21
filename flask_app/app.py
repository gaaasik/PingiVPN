import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime

import redis.asyncio as redis
import aiosqlite
import pytz
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from config_flask_redis import DATABASE_PATH


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

# Глобальная переменная Redis-клиента
redis_client: redis.Redis = None


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

    # Инициализация Redis
    redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
    logger.info("Redis успешно инициализирован.")

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

        # Отправляем в Redis
        await redis_client.lpush("payment_notifications", json.dumps(message))
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


@app.get("/")
async def home():
    return {"message": "Hello, this is FastAPI application!"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
