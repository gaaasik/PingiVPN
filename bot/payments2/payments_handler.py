import asyncio
import json
import logging
import os

import redis
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
from yookassa import Configuration, Payment
from aiogram import Router, types, Bot

from bot.payments2.if_user_sucsess_pay import update_user_subscription_db, handle_post_payment_actions
from flask_app.all_utils_flask import logger
from bot.handlers.admin import send_admin_log, ADMIN_CHAT_IDS

load_dotenv()
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
listen_task = None  # Переменная для хранения задачи прослушивания

# Настройка API Юкассы
Configuration.account_id = os.getenv('SHOPID')
Configuration.secret_key = os.getenv('API_KEY')
REDIS_QUEUE = 'payment_notifications'

# Инициализация Redis клиента
redis_client = redis.Redis(host='localhost', port=6379, db=0)
router = Router()


async def run_listening_for_duration(bot: Bot, duration: int):
    """Запускает прослушивание Redis на определенный промежуток времени."""
    global listen_task
    try:
        # Запускаем задачу прослушивания
        listen_task = asyncio.create_task(listen_to_redis_queue(bot))
        await asyncio.sleep(duration)  # Ждем указанное время
        listen_task.cancel()  # Завершаем прослушивание после истечения времени
        logging.info("Задача прослушивания была завершена после указанного времени.")
    except asyncio.CancelledError:
        logging.info("Задача прослушивания была отменена.")
    except Exception as e:
        logging.error(f"Ошибка при запуске прослушивания: {e}")@router.callback_query(lambda c: c.data == 'payment_199')
async def process_callback_query(callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    user_id = callback_query.message.from_user.id
    bot = callback_query.message.bot
    global listen_task
    if listen_task is None or listen_task.done():
        listen_task = asyncio.create_task(run_listening_for_duration(bot, 60 * 60))

    if chat_id == 456717505:
        one_time_id, one_time_link, _ = create_one_time_payment(chat_id)
        text_payment = (
            "Вы подключаете подписку на наш сервис с помощью платёжной системы Юkassa\n\n"
            "Стоимость подписки на 1 месяц: 199р 👇👇👇\n"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Оплатить 199р", url=one_time_link)]]
        )
        await bot.send_message(chat_id=chat_id, text=text_payment, reply_markup=keyboard)
    else:
        await bot.send_message(chat_id=chat_id, text="Оплата скоро будет доступна")
        username = callback_query.message.from_user.username
        await send_admin_log(bot, message=f"@{username} - нажал кнопку оплатить, но у него ничего не вышло )) ID чата: {chat_id})")
    await callback_query.answer()


# Функция для создания разового платежа
def create_one_time_payment(user_id):
    payment = Payment.create({
        "amount": {"value": "199.00", "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": WEBHOOK_URL},
        "capture": True,
        "description": "Подписка на Telegram-бот",
        "metadata": {"user_id": user_id}
    })
    return payment.id, payment.confirmation.confirmation_url, '0'

async def listen_to_redis_queue(bot: Bot):
    """Прослушивание очереди Redis для обработки сообщений о платежах."""
    logging.info("Начало прослушивания очереди tasks")
    while True:
        try:
            logging.info("Попытка извлечь задачу из очереди Redis")
            task_data = await asyncio.to_thread(redis_client.lpop, 'payment_notifications')

            if task_data:
                logging.info(f"Извлечена задача из Redis: {task_data}")

                try:
                    task = json.loads(task_data)
                    logging.info(f"Задача после парсинга JSON: {task}")
                except json.JSONDecodeError as e:
                    logging.error(f"Ошибка декодирования JSON: {e}, данные: {task_data}")
                    continue

                # Передаем всю задачу в функцию process_payment_message, включая все данные
                await process_payment_message(json.dumps(task), bot)
            else:
                logging.info("Очередь Redis пуста, ждем следующую задачу")

            await asyncio.sleep(1)

        except redis.exceptions.ConnectionError as e:
            logging.error(f"Ошибка подключения к Redis: {e}")
            await asyncio.sleep(5)
        except Exception as e:
            logging.error(f"Ошибка при обработке сообщения из Redis: {e}")
            await asyncio.sleep(5)


async def process_payment_message(message: str, bot: Bot):
    """Обработка сообщения из Redis с информацией о платеже."""
    try:
        logging.info(f"Начинаем обработку сообщения: {message}")
        data = json.loads(message)
        user_id = data.get('user_id')
        amount = data.get('amount')
        currency = data.get('currency')
        status = data.get('status')

        # Проверка наличия всех необходимых данных
        if not all([user_id, amount, currency, status]):
            logger.error(f"Некорректное сообщение о платеже: {data}")
            return

        # Формирование сообщения в зависимости от статуса платежа
        if status == 'payment.succeeded':
            await update_user_subscription_db(user_id)
            await handle_post_payment_actions(bot, user_id)
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

        # Останавливаем задачу прослушивания, если необходимо
        global listen_task
        if listen_task and not listen_task.done():
            listen_task.cancel()

    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON: {e}, данные: {message}")
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения о платеже: {e}")
