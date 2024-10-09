import asyncio
import json
import logging
import os

import redis
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
from yookassa import Configuration, Payment
from aiogram import Router, types, Bot

from flask_app.all_utils_flask import logger

from bot.handlers.admin import send_admin_log

load_dotenv()
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Настройка API Юкассы
Configuration.account_id = os.getenv('SHOPID')# Ваш shopId
Configuration.secret_key = os.getenv('API_KEY')  # Ваш секретный ключ API
REDIS_QUEUE = 'payment_notifications'

# Инициализация Redis клиента
redis_client = redis.Redis(host='localhost', port=6379, db=0)
router = Router()

@router.callback_query(lambda c: c.data == 'payment_199')
async def process_callback_query(callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    user_id = callback_query.message.from_user.id
    bot = callback_query.message.bot
    if chat_id == 456717505:

        # Создаем платёж и получаем ссылку
        one_time_id, one_time_link, one_time_payment_method_id = create_one_time_payment(chat_id)

        # Текст сообщения
        text_payment = (
            "Вы подключаете подписку на наш сервис с помощью\n"
            "платёжной системы Юkassa\n\n"
            "Стоимость подписки на 1 месяц: 199р 👇👇👇\n"
        )

        # Создаем клавиатуру с кнопкой
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Оплатить 199р", url=one_time_link)]
            ]
        )
        # Отправляем сообщение с текстом и клавиатурой
        await bot.send_message(
            chat_id=chat_id,
            text=  text_payment,
            reply_markup=keyboard
        )
    else:
        # Отправляем сообщение с текстом и клавиатурой
        await bot.send_message(
            chat_id=chat_id,
            text="Оплата скоро будет доступна"#,
            #reply_markup=keyboard
        )

        username = callback_query.message.from_user.username
        await send_admin_log(bot,
            message=f"@{username} - нажал кнопку оплатить, но у него ничего не вышло )) ID чата: {chat_id})")
    # Подтверждаем callback_query, чтобы избежать зависания
    await callback_query.answer()


# Функция для создания разового платежа
def create_one_time_payment(user_id):
    payment = Payment.create({
        "amount": {
            "value": "199.00",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": WEBHOOK_URL
        },
        "capture": True,
        "description": "Подписка на Telegram-бот",
        "metadata": {
            "user_id": user_id
        }
    })
    return payment.id, payment.confirmation.confirmation_url, '0'


async def listen_to_redis_queue(bot: Bot):
    """Прослушивание очереди Redis для обработки сообщений о платежах."""
    logging.info("Начало прослушивания очереди tasks")
    while True:
        try:
            logging.info("Попытка извлечь задачу из очереди Redis")

            # Выполняем синхронный запрос к Redis в отдельном потоке
            task_data = await asyncio.to_thread(redis_client.lpop, 'payment_notifications')

            if task_data:
                logging.info(f"Извлечена задача из Redis: {task_data}")

                try:
                    task = json.loads(task_data)
                    logging.info(f"Задача после парсинга JSON: {task}")
                except json.JSONDecodeError as e:
                    logging.error(f"Ошибка декодирования JSON: {e}, данные: {task_data}")
                    # Если данные не являются корректным JSON, переходим к следующей итерации
                    continue

                user_id = task.get('user_id')
                amount = task.get('amount')
                currency = task.get('currency')
                status = task.get('status')

                logging.info(f"Обработка сообщения для пользователя {user_id}")

                # Передаем всю задачу в функцию process_payment_message, включая все данные
                await process_payment_message(json.dumps(task), bot)
            else:
                logging.info("Очередь Redis пуста, ждем следующую задачу")

            # Ждем перед следующим запросом к Redis
            await asyncio.sleep(1)

        except redis.exceptions.ConnectionError as e:
            logging.error(f"Ошибка подключения к Redis: {e}")
            # Ждем перед повторной попыткой подключения
            await asyncio.sleep(5)
        except Exception as e:
            logging.error(f"Ошибка при обработке сообщения из Redis: {e}")
            # Ждем перед повторной попыткой в случае любой другой ошибки
            await asyncio.sleep(5)


async def process_payment_message(message: str, bot: Bot):
    """Обработка сообщения из Redis с информацией о платеже."""
    try:
        logging.info(f"Начинаем обработку сообщения: {message}")

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
        logger.error(f"Ошибка декодирования JSON: {e}, данные: {message}")
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения о платеже: {e}")

