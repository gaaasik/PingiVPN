import asyncio
import json
import logging
import os

import redis
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
from yookassa import Configuration, Payment
from aiogram import Router, types, Bot

from bot.handlers.cleanup import register_message_type, delete_important_message, store_message, \
    delete_unimportant_messages
from bot.payments2.if_user_sucsess_pay import handle_post_payment_actions
from bot.payments2.payments_db import reset_user_data_db
from flask_app.all_utils_flask_db import logger
from bot.handlers.admin import send_admin_log, ADMIN_CHAT_IDS
from bot.utils.db import get_user_subscription_status, update_payment_status, update_user_subscription_db

load_dotenv()
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
listen_task = None  # Переменная для хранения задачи прослушивания

# Настройка API Юкассы
Configuration.account_id = os.getenv('SHOPID')
Configuration.secret_key = os.getenv('API_KEY')
REDIS_QUEUE = 'payment_notifications'

# Инициализация Redis клиента
redis_client = redis.Redis(host='217.25.91.109', port=6379, db=0)
router = Router()


#нажатие на кнопку оплатить 199 рублей - отправялет сообщение с ссылкой на оплату
@router.callback_query(lambda c: c.data == 'payment_199')
async def process_callback_query(callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    user_id = callback_query.message.from_user.id
    bot = callback_query.message.bot
    await delete_unimportant_messages(chat_id, bot)
    subscription_status = await get_user_subscription_status(chat_id)
    print(subscription_status)
    # if chat_id in ADMIN_CHAT_IDS or chat_id==1388513042:
    if subscription_status == "waiting_pending" or subscription_status == "new_user":

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
        sent_message = await bot.send_message(
            chat_id=chat_id,
            text=text_payment,
            reply_markup=keyboard
        )
        await register_message_type(chat_id, sent_message.message_id, "msg_with_pay_url", bot)
        print("text = ", sent_message.text)
    elif subscription_status == "active":
        # Отправляем сообщение с текстом и клавиатурой
        text_msg = "Ваша подписка активна на месяц"
        sent_message = await bot.send_message(
            chat_id=chat_id,
            text=text_msg,
        )
        await store_message(chat_id, sent_message.message_id, text_msg, 'bot')

    # else:
    #     # Отправляем сообщение с текстом и клавиатурой
    #     await bot.send_message(
    #         chat_id=chat_id,
    #         text="Оплата скоро будет доступна"  #,
    #         #reply_markup=keyboard
    #     )

    username = callback_query.message.chat.username
    await send_admin_log(bot,
                         message=f"@{username}  chat_id = {chat_id}  - нажал кнопку оплатить ID чата: {chat_id})")
    # Подтверждаем callback_query, чтобы избежать зависания
    await callback_query.answer()


@router.callback_query(lambda c: c.data == 'delete_user')
async def delete_user_callback(callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id  # Используем chat_id вместо user_id
    user_id = callback_query.message.from_user.id
    bot = callback_query.message.bot

    # Вызываем функцию сброса данных пользователя
    await reset_user_data_db(chat_id)

    # Отправляем сообщение пользователю
    await bot.send_message(
        chat_id=chat_id,
        text="Вы удалены из базы данных."
    )

    # Подтверждаем callback_query, чтобы избежать зависания
    await callback_query.answer()


async def run_listening_redis_for_duration(bot: Bot):
    """Запускает прослушивание Redis на определенный промежуток времени."""
    global listen_task
    try:
        # Запускаем задачу прослушивания
        listen_task = asyncio.create_task(listen_to_redis_queue(bot))

    except asyncio.CancelledError:
        logging.info("Задача прослушивания была отменена.")
        await send_admin_log(bot, "Warning - очредь редис заверешиоа работу")
    except Exception as e:
        logging.error(f"Ошибка при запуске прослушивания: {e}") @ router.callback_query(
            lambda c: c.data == 'payment_199')
        await send_admin_log(bot, "Warning - очредь редис заверешиоа работу")


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
            #logging.info("Попытка извлечь задачу из очереди Redis")
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
                a = 1
                #logging.info("Очередь Redis пуста, ждем следующую задачу")

            await asyncio.sleep(3)

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
        payment_id = data.get('payment_id')

        # print(data)
        #добавить дату платежа

        # Проверка наличия всех необходимых данных
        if not all([user_id, amount, currency, status, payment_id]):
            logger.error(f"Некорректное сообщение о платеже: {data}")
            return
        # обноление таблицы payment
        await update_payment_status(payment_id, user_id, amount, currency, status)
        await send_admin_log(bot, f"Пойман платеж от {user_id}, c статусом {status}")
        #await delete_important_message(user_id, "msg_with_pay_url", bot)

        ###############################################
        # Формирование сообщения в зависимости от статуса платежа
        if status == 'payment.succeeded':
            await update_user_subscription_db(user_id)
            await handle_post_payment_actions(bot, user_id)
        #дрписать canceled уведомления

        # elif status == 'payment.waiting_for_capture':
        #     text = f"Ваш платеж на сумму {amount} {currency} ожидает подтверждения."
        #
        # elif status == 'payment.canceled':
        #     text = f"Ваш платеж на сумму {amount} {currency} был отменен."
        #
        # elif status == 'refund.succeeded':
        #     text = f"Ваш возврат на сумму {amount} {currency} был не обработан."
        # else:
        #     text = f"Обновление платежа: {status}. Сумма: {amount} {currency}."

        #logger.info(f"Сообщение отправлено пользователю {user_id}: {text}")

        await delete_important_message(user_id, "msg_with_pay_url", bot)
        # Останавливаем задачу прослушивания, если необходимо
        # global listen_task
        # if listen_task and not listen_task.done():
        #     listen_task.cancel()

    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON: {e}, данные: {message}")
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения о платеже: {e}")
