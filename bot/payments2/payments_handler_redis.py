import asyncio
import json
import logging
import os
from datetime import datetime, timedelta

import redis
from dotenv import load_dotenv
from yookassa import Configuration, Payment
from aiogram import Router, types, Bot
from models.UserCl import UserCl
from bot.handlers.cleanup import delete_important_message
from bot.payments2.if_user_sucsess_pay import handle_post_payment_actions
from flask_app.all_utils_flask_db import logger
from bot.handlers.admin import send_admin_log
from bot.database.db import  update_payment_status, update_user_subscription_db

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
        logging.error(f"Ошибка при запуске прослушивания: {e}")
        await send_admin_log(bot, "Warning - очредь редис заверешиоа работу")


async def create_one_time_payment(user_id, user_name, user_email):
    payment = Payment.create({
        "amount": {
            "value": "199.00",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/PingiVPN_bot"  # это URL, куда пользователь будет перенаправлен после оплаты
        },
        "capture": True,  # автоматически подтверждаем оплату
        "description": "Подписка на канал",
        "metadata": {
            "user_id": user_id,
            "user_name": user_name  # метаданные, для идентификации пользователя
        },
        "receipt": {
            "customer": {
                "email": user_email  # Здесь будет email клиента
            },
            "tax_system_code": 2, # УСН доходы
            "items": [
                {
                    "description": "Подписка на канал",  # Описание услуги или товара
                    "quantity": "1.00",  # Количество единиц товара или услуги
                    "amount": {
                        "value": "199.00",  # Цена товара или услуги
                        "currency": "RUB"
                    },
                    "vat_code": "1",
                    "payment_mode": "full_payment",  # Тип оплаты (полный расчет)
                    "payment_subject": "service"  # Предмет оплаты (товар или услуга)
                }
            ]
        }
    })

    return payment.id, payment.confirmation.confirmation_url


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
                pass
                #logging.info("Очередь Redis пуста, ждем следующую задачу")

            await asyncio.sleep(4)

        except redis.exceptions.ConnectionError as e:
            logging.error(f"Ошибка подключения к Redis: {e}")
            await asyncio.sleep(5)
        except Exception as e:
            logging.error(f"Ошибка при обработке сообщения из Redis: {e}")
            await asyncio.sleep(5)

#обновление базы данных при успешной оплате
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
        # Проверка наличия всех необходимых данных
        if not all([user_id, amount, currency, status, payment_id]):
            await send_admin_log(bot,f"Некорректное сообщение о платеже: {data}")
            return




        # обноление таблицы payment
        #await update_payment_status(payment_id, user_id, amount, currency, status)
        await send_admin_log(bot, f"Пойман платеж от {user_id}, c статусом {status}")


        ###############################################
        # Формирование сообщения в зависимости от статуса платежа
        if status == 'payment.succeeded':
            us = await UserCl.load_user(user_id)

            # Устанавливаем статус ключа на "active"
            await us.servers[0].status_key.set("active")

            # Получаем текущую дату
            current_date = datetime.now()

            # Получаем дату окончания ключа из базы
            date_key_off = await us.servers[0].date_key_off.get()

            # Преобразуем строку в объект datetime, используя формат "DD.MM.YYYY HH:MM:SS"
            date_key_off = datetime.strptime(date_key_off, "%d.%m.%Y %H:%M:%S")
            # Проверяем, истекла ли дата окончания ключа
            if date_key_off < current_date:
                # Если дата истекла, устанавливаем новую дату на 30 дней от текущего момента
                new_expiry_date = current_date + timedelta(days=30)
            else:
                # Если дата не истекла, добавляем 30 дней к существующей дате окончания
                new_expiry_date = date_key_off + timedelta(days=30)

            # Преобразуем новую дату обратно в строку в формате "DD.MM.YYYY HH:MM:SS"
            new_expiry_date_str = new_expiry_date.strftime("%d.%m.%Y %H:%M:%S")

            # Сохраняем новую дату окончания и обновляем статус платного ключа
            await us.servers[0].date_key_off.set(new_expiry_date_str)
            await us.servers[0].has_paid_key.set(1)

            # Выполнение последующих действий после оплаты
            await handle_post_payment_actions(bot, user_id)


    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON: {e}, данные: {message}")
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения о платеже: {e}")

