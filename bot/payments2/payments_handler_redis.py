import asyncio
import json
import logging
import os
from datetime import datetime, timedelta

import aiosqlite
import pytz
import redis
from dotenv import load_dotenv
from yookassa import Configuration, Payment
from aiogram import Router, types, Bot
from models.UserCl import UserCl
from bot.handlers.cleanup import delete_important_message
from bot.payments2.if_user_sucsess_pay import handle_post_payment_actions
#from fastapi_app.all_utils_flask_db import logger
from bot.handlers.admin import send_admin_log
from bot.database.db import  update_payment_status, update_user_subscription_db

load_dotenv()
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
listen_task = None  # Переменная для хранения задачи прослушивания
db_path = os.getenv('database_path_local')
# Настройка API Юкассы
Configuration.account_id = os.getenv('SHOPID')
Configuration.secret_key = os.getenv('API_KEY')
REDIS_QUEUE = 'payment_notifications'
PASSWORD_REDIS = os.getenv('password_redis')

ip = os.getenv('ip_redis_server')
# Инициализация Redis клиента
redis_client = redis.Redis(host=ip , port=6379, password=PASSWORD_REDIS, db=0)
router = Router()
# async def save_payment_to_db(chat_id, payment_id, amount, currency, status, payment_method_id, payment_json):
#     # Определяем московский часовой пояс
#     moscow_tz = pytz.timezone("Europe/Moscow")
#
#     # Время создания и обновления записи в московском времени
#     created_at = datetime.now(moscow_tz).strftime("%Y-%m-%d %H:%M:%S")
#     updated_at = created_at
#
#     async with aiosqlite.connect(db_path) as db:
#         await db.execute("""
#             INSERT INTO payments (chat_id, payment_id, amount, currency, status, payment_method_id, created_at, updated_at, payment_json)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """, (chat_id, payment_id, amount, currency, status, payment_method_id, created_at, updated_at, json.dumps(payment_json)))
#         await db.commit()

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
            await asyncio.sleep(3)    #logging.info("Очередь Redis пуста, ждем следующую задачу")
                #logging.info("Очередь Redis пуста, ждем следующую задачу")



        except redis.exceptions.ConnectionError as e:
            logging.error(f"Ошибка подключения к Redis: {e}")
            await asyncio.sleep(5)
        except Exception as e:
            logging.error(f"Ошибка при обработке сообщения из Redis: {e}")
            await asyncio.sleep(5)

#обновление базы данных при успешной оплате
# обноление базы данных при успешной оплате
async def process_payment_message(message: str, bot: Bot):
    """Обработка сообщения из Redis с информацией о платеже."""
    try:
        logging.info(f"Начинаем обработку сообщения: {message}")
        data = json.loads(message)
        logging.info(f"Распарсенные данные сообщения: {data}")

        # Извлечение необходимых данных
        chat_id = data.get('user_id')
        amount = data.get('amount')
        currency = data.get('currency')
        status = data.get('status')
        payment_id = data.get('payment_id')
        payment_json = data.get('payload_json')
        logging.info(f"Данные пользователя: user_id={chat_id}, amount={amount}, currency={currency}, status={status}, payment_id={payment_id}")

        # Проверка наличия всех необходимых данных
        if not all([chat_id, amount, currency, status, payment_id]):
            await send_admin_log(bot, f"Некорректное сообщение о платеже: {data}")
            logging.error("Сообщение не содержит всех необходимых данных.")
            return
        #сохраняем уже в fastapi
        # await save_payment_to_db(
        #     chat_id=chat_id,
        #     payment_id=payment_id,
        #     amount=amount,
        #     currency=currency,
        #     status=status,
        #     payment_method_id=payment_id,
        #     payment_json=payment_json
        # )
        # logging.info("Платеж сохранён в базе данных.")

        us = await UserCl.load_user(chat_id)
        user_name = us.user_login.get()

        ###############################################
        # Формирование сообщения в зависимости от статуса платежа
        if status == 'payment.succeeded':

            #await send_admin_log(bot, f"Пойман Успешный платеж от {chat_id}, @{user_name} c статусом {status}")
            logging.info(f"Платеж успешно завершён для пользователя {chat_id}. Загружаем данные пользователя...")


            # Логирование серверов пользователя
            logging.info(f"Сервера пользователя: {us.servers}")
            if not us.servers:
                logging.error(f"У пользователя {chat_id} нет серверов. Завершаем обработку.")
                return

            server = us.servers[0]
            logging.info(f"Первый сервер пользователя: {server}")

            # Устанавливаем статус ключа на "active"
            await server.status_key.set("active")
            logging.info(f"Статус ключа для сервера пользователя {chat_id} установлен на 'active'.")

            # Получаем текущую дату
            current_date = datetime.strptime(datetime.now().strftime("%d.%m.%Y %H:%M:%S"), "%d.%m.%Y %H:%M:%S")
            logging.info(f"Текущая дата: {current_date}")

            # Получаем дату окончания ключа из базы
            date_key_off = await server.date_key_off.get()
            logging.info(f"Дата окончания ключа: {date_key_off}")

            # Преобразуем строку в объект datetime
            date_key_off = datetime.strptime(date_key_off, "%d.%m.%Y %H:%M:%S")
            if date_key_off < current_date:
                logging.info("Ключ истёк. Устанавливаем новую дату на 30 дней от текущей.")
                new_expiry_date = current_date + timedelta(days=31)
            else:
                logging.info("Ключ активен. Добавляем 30 дней к текущей дате окончания.")
                new_expiry_date = date_key_off + timedelta(days=31)

            # Преобразуем новую дату обратно в строку
            new_expiry_date_str = new_expiry_date.strftime("%d.%m.%Y %H:%M:%S")
            logging.info(f"Новая дата окончания ключа: {new_expiry_date_str}")

            # Сохраняем новую дату окончания и обновляем статус платного ключа
            await server.date_payment_key.set(str(current_date.strftime("%d.%m.%Y %H:%M:%S")))
            await server.date_key_off.set(new_expiry_date_str)
            logging.info(f"Дата окончания ключа обновлена для сервера пользователя {chat_id}.")
            # Увеличиваем значение has_paid_key на 1
            current_value = int(await server.has_paid_key.get())
            await server.has_paid_key.set(current_value + 1)
            logging.info(f"Статус платного ключа установлен на 1 для сервера пользователя {chat_id}.")

            # Выполнение последующих действий после оплаты
            await handle_post_payment_actions(bot, chat_id)
            logging.info(f"Постоплатные действия выполнены для пользователя {chat_id}.")
        else:
            await send_admin_log(bot, f"👺👺Незавершенный платеж от {chat_id}, @{user_name}")
    except json.JSONDecodeError as e:
        logging.info(f"Ошибка декодирования JSON: {e}, данные: {message}")
    except Exception as e:
        logging.info(f"Ошибка при обработке сообщения о платеже: {e}")
