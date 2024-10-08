import asyncio
import json
import logging
import redis
from aiogram import Bot

# Настройка подключения к Redis
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_QUEUE = 'payment_notifications'

# Инициализация клиента Redis
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

# Инициализация логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def listen_to_redis_queue(bot: Bot):
    """Прослушивание очереди Redis для обработки сообщений о платежах."""
    logger.info(f"Начало прослушивания очереди {REDIS_QUEUE}")

    while True:
        try:
            # Используем asyncio.to_thread для выполнения блокирующего вызова в отдельном потоке
            _, message = await asyncio.to_thread(redis_client.blpop, REDIS_QUEUE)
            logger.info(f"Сообщение пришло в очередь Redis: {message}")
            await process_payment_message(message, bot)
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения из Redis: {e}")


async def process_payment_message(message: str, bot: Bot):
    """
    Обработка сообщения из Redis с информацией о платеже.

    :param message: JSON-строка с информацией о платеже, полученная из Redis.
    :param bot: Экземпляр Telegram-бота для отправки сообщений пользователям.
    """
    try:
        # Декодируем JSON-строку в Python-словарь
        data = json.loads(message)
        user_id = data.get('user_id')
        amount = data.get('amount')
        currency = data.get('currency')
        status = data.get('status')

        # Проверка, что все нужные данные присутствуют
        if not all([user_id, amount, currency, status]):
            logger.error(f"Некорректное сообщение о платеже: {data}")
            return

        # Формируем текст сообщения в зависимости от статуса платежа
        if status == 'payment.succeeded':
            text = f"Ваш платеж на сумму {amount} {currency} успешно завершен!"
        elif status == 'payment.waiting_for_capture':
            text = f"Ваш платеж на сумму {amount} {currency} ожидает подтверждения."
        elif status == 'payment.canceled':
            text = f"Ваш платеж на сумму {amount} {currency} был отменен."
        elif status == 'refund.succeeded':
            text = f"Ваш возврат на сумму {amount} {currency} был успешно обработан."
        else:
            text = f"Обновление платежа: {status}. Сумма: {amount} {currency}."

        # Отправляем сообщение пользователю
        await bot.send_message(chat_id=user_id, text=text)
        logger.info(f"Сообщение отправлено пользователю {user_id}: {text}")

    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON: {e}")
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения о платеже: {e}")