import asyncio
import json
import logging
import os

import redis
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
from yookassa import Configuration, Payment
from aiogram import Router, types, Bot

from bot.handlers.cleanup import delete_important_message, store_message, \
    delete_unimportant_messages, register_message_type
from bot.handlers.status import generate_status_message
from bot.payments2.if_user_sucsess_pay import handle_post_payment_actions
from bot.payments2.payments_db import reset_user_data_db
from flask_app.all_utils_flask_db import logger
from bot.handlers.admin import send_admin_log
from bot.database.db import get_user_subscription_status, update_payment_status, update_user_subscription_db, \
    save_user_email_to_db

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


# Определение машины состояний для ввода email
class PaymentForm(StatesGroup):
    awaiting_email = State()  # Состояние для ввода email


# 1. Обработчик нажатия на кнопку "Оплатить 199 рублей"
@router.callback_query(lambda c: c.data == 'payment_199')
async def handle_payment_request(callback_query: types.CallbackQuery, state: FSMContext):
    chat_id = callback_query.message.chat.id
    user_id = callback_query.message.from_user.id
    bot = callback_query.message.bot

    # Удаляем предыдущие сообщения
    await delete_unimportant_messages(chat_id, bot)

    # Проверяем статус подписки
    subscription_status = await get_user_subscription_status(chat_id)

    if subscription_status in ["waiting_pending", "new_user", "blocked"]:
        # Запрашиваем email
        await request_user_email(chat_id, bot, state)
        await state.set_state(PaymentForm.awaiting_email)  # Устанавливаем состояние ожидания email
    elif subscription_status == "active":
        sent_message = await bot.send_message(chat_id, text="Ваша подписка активна на месяц")
        await store_message(chat_id, sent_message.message_id, sent_message.text, "bot")
    else:
        sent_message2 = await bot.send_message(chat_id, text="Оплата скоро будет доступна")
        await store_message(chat_id, sent_message2.message_id, sent_message2.text, "bot")

    # Логируем нажатие
    username = callback_query.message.chat.username
    await send_admin_log(bot, message=f"@{username} нажал кнопку 'Оплатить', chat_id = {chat_id}")

    # Подтверждаем callback_query
    await callback_query.answer()


# 2. Функция запроса email
async def request_user_email(chat_id: int, bot: Bot, state: FSMContext):
    # Удаляем предыдущие сообщения
    await delete_unimportant_messages(chat_id, bot)
    text = "Пожалуйста, введите ваш email для отправки чека:"

    # Добавляем кнопку "Отменить"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Отменить платеж", callback_data="cancel_payment")]
        ]
    )

    sent_message = await bot.send_message(chat_id, text=text, reply_markup=keyboard)
    await register_message_type(chat_id, sent_message.message_id, "request_email_msg", bot)

    # Устанавливаем состояние ожидания email
    await state.set_state(PaymentForm.awaiting_email)

    # Запускаем таймер для сброса состояния через 1 час
    asyncio.create_task(start_email_timeout(chat_id, state))


# 3. Валидация email
@router.message(PaymentForm.awaiting_email)
async def handle_email_input(message: types.Message, state: FSMContext):
    email = message.text
    user_id = message.from_user.id
    user_name = message.from_user.username
    chat_id = message.chat.id
    bot = message.bot
    await delete_unimportant_messages(chat_id, bot)
    # Валидация email
    if validate_email(email):
        # Сохраняем email во временном состоянии FSM
        await state.update_data(email=email)

        # Отправляем сообщение с подтверждением email
        text = f"Отправить чек на почту {email}?"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Да", callback_data="confirm_email")],  # Кнопка "Да" на отдельной строке
                [  # Кнопки "Изменить почту" и "Отменить платеж" на одной строке
                    InlineKeyboardButton(text="Изменить почту", callback_data="edit_email"),
                    InlineKeyboardButton(text="Отменить платеж", callback_data="cancel_payment")
                ]
            ]
        )
        sent_message = await bot.send_message(chat_id, text=text, reply_markup=keyboard)
        await store_message(chat_id, sent_message.message_id, sent_message.text, "bot")

    else:
        # Сообщаем о неверном формате и просим ввести повторно
        send_message = await bot.send_message(chat_id, "Неверный формат email. Пожалуйста, введите корректный email.")
        await store_message(send_message.chat.id, send_message.message_id, send_message.text, "bot")


@router.callback_query(lambda c: c.data in ["confirm_email", "edit_email"])
async def handle_email_confirmation(callback_query: types.CallbackQuery, state: FSMContext):
    chat_id = callback_query.message.chat.id
    user_name = callback_query.message.chat.username
    bot = callback_query.message.bot

    if callback_query.data == "confirm_email":
        # Пользователь подтвердил email
        await delete_unimportant_messages(chat_id, bot)
        await delete_important_message(chat_id, "request_email_msg", bot)
        data = await state.get_data()
        email = data.get("email")
        await save_user_email_to_db(chat_id,email)
        # Формируем ссылку на оплату
        one_time_id, one_time_link = await create_one_time_payment(chat_id, user_name, email)

        # Отправляем ссылку на оплату
        await send_payment_link(chat_id, one_time_link, bot)

        # Сбрасываем состояние
        await state.clear()

    elif callback_query.data == "edit_email":
        # Пользователь хочет изменить email, возвращаем его в состояние ожидания email
        await request_user_email(chat_id, bot,state)
        await state.set_state(PaymentForm.awaiting_email)

    # Подтверждаем callback_query
    await callback_query.answer()
async def start_email_timeout(chat_id: int, state: FSMContext, timeout: int = 3600):
    await asyncio.sleep(timeout)  # Ожидание в течение 1 часа
    current_state = await state.get_state()
    if current_state == PaymentForm.awaiting_email:
        await state.clear()  # Сбрасываем состояние, если время истекло

# 4. Функция отмены платежа

@router.callback_query(lambda c: c.data == 'cancel_payment')
async def handle_cancel_payment(callback_query: types.CallbackQuery, state: FSMContext):
    chat_id = callback_query.message.chat.id
    bot = callback_query.message.bot
    await delete_unimportant_messages(chat_id,bot)
    await state.clear()  # Завершаем любое текущее состояние

    await bot.send_message(chat_id, "Платеж был отменен.")

    #отправляем сообщение с статусом

    # Используем функцию generate_status_message для получения текста и клавиатуры.
    status_message, keyboard = await generate_status_message(chat_id)
    # Отправляем новое сообщение с информацией об аккаунте и кнопкой оплаты, если она есть.
    sent_message = await bot.send_message(chat_id, status_message, parse_mode="Markdown", reply_markup=keyboard)

    # Сохраняем сообщение в базе, если оно было успешно отправлено.
    if sent_message and sent_message.message_id:
        await store_message(chat_id, sent_message.message_id, status_message, 'bot')
        await register_message_type(chat_id, sent_message.message_id, 'account_status', bot)

    await callback_query.answer()


# Вспомогательные функции

# Функция валидации email
def validate_email(email: str) -> bool:
    import re
    # Пример простой регулярки для проверки email
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w{2,4}$"
    return bool(re.match(pattern, email))


# Функция отправки ссылки на оплату
async def send_payment_link(chat_id: int, payment_link: str, bot: Bot):
    text_payment = (
        "Вы подключаете подписку на наш сервис с помощью\n"
        "платёжной системы Юkassa\n\n"
        "Стоимость подписки на 1 месяц: 199р 👇👇👇\n"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Оплатить 199р", url=payment_link)]
        ]
    )
    sent_message = await bot.send_message(chat_id=chat_id, text=text_payment, reply_markup=keyboard)

    # Логика для сохранения отправленного сообщения, если необходимо


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
                a = 1
                #logging.info("Очередь Redis пуста, ждем следующую задачу")

            await asyncio.sleep(4)

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
