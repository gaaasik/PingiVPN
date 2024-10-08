import redis
import json
from  flask_app.config_flask_redis import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_QUEUE
from  flask_app.all_utils_flask import logger
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD)
import json
from redis import asyncio as aioredis

async def process_payment_message(message, bot):
    """Обработка сообщения из Redis с информацией о платеже."""
    try:
        data = json.loads(message)
        user_id = data.get('user_id')
        amount = data.get('amount')
        currency = data.get('currency')
        payment_status = data.get('status')

        # Отправка сообщения пользователю в зависимости от статуса платежа
        if payment_status == 'payment.succeeded':
            await bot.send_message(
                user_id,
                f"Ваш платеж на сумму {amount} {currency} успешно завершен! Спасибо за оплату!"
            )
            logger.info(f"Уведомление об успешном платеже отправлено пользователю {user_id}.")

        elif payment_status == 'payment.waiting_for_capture':
            await bot.send_message(
                user_id,
                f"Ваш платеж на сумму {amount} {currency} ожидает подтверждения. Пожалуйста, подождите."
            )
            logger.info(f"Уведомление об ожидании подтверждения отправлено пользователю {user_id}.")

        elif payment_status == 'payment.canceled':
            await bot.send_message(
                user_id,
                f"Ваш платеж на сумму {amount} {currency} был отменен. Если это ошибка, свяжитесь с поддержкой."
            )
            logger.info(f"Уведомление об отмене платежа отправлено пользователю {user_id}.")

        elif payment_status == 'refund.succeeded':
            await bot.send_message(
                user_id,
                f"Возврат на сумму {amount} {currency} успешно завершен. Средства будут зачислены на ваш счет в ближайшее время."
            )
            logger.info(f"Уведомление об успешном возврате отправлено пользователю {user_id}.")

        else:
            logger.warning(f"Неизвестный статус платежа: {payment_status} для пользователя {user_id}.")

    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON: {e}")
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения о платеже: {e}")

async def listen_to_redis_queue(bot):
    """Прослушивание очереди Redis для обработки сообщений."""
    logger.info(f"Начало прослушивания очереди {REDIS_QUEUE}")
    redis_client = aioredis.from_url("redis://localhost:6379")
    while True:
        print("Ожидаем сообщения из Redis...")
        _, message = await redis_client.blpop("payment_notifications")
        print(f"Получено сообщение: {message}")
        await process_payment_message(message,bot)



