# menu_buy_vpn.py
import asyncio

from aiogram import Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery

from bot.database.db import get_user_subscription_status
from bot.handlers.admin import send_admin_log
from bot.handlers.cleanup import register_message_type
from bot.payments2.payments_handler_redis import create_one_time_payment
from models.UserCl import UserCl

# Инициализация роутера
router = Router()

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

# Определение машины состояний для ввода email
class PaymentForm(StatesGroup):
    awaiting_email = State()  # Состояние для ввода email
# Вспомогательные функции

# Функция валидации email
def validate_email(email: str) -> bool:
    import re
    # Пример простой регулярки для проверки email
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w{2,4}$"
    return bool(re.match(pattern, email))


# 2. Функция запроса email
async def request_user_email(chat_id: int, bot: Bot, state: FSMContext):
    # Удаляем предыдущие сообщения

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


# 1. Обработчик нажатия на кнопку "Оплатить 199 рублей"

# Основной обработчик при нажатии на кнопку "Оплатить 199 рублей"
@router.callback_query(lambda c: c.data == 'payment_199')
async def handle_payment_request(callback_query: types.CallbackQuery, state: FSMContext):
    chat_id = callback_query.message.chat.id
    bot = callback_query.message.bot

    # Загружаем пользователя и проверяем статус подписки
    us = await UserCl.load_user(chat_id)
    if not us:
        await bot.send_message(chat_id, "Ошибка загрузки данных пользователя.")
        return

    # Получаем статус ключа
    if await us.count_key.get() == 0:
        await bot.send_message(chat_id, "У вас нет ключа для оплаты, добавьте ключ ")
        return

    status_key = await us.servers[0].status_key.get()

    # Если статус пробный период или заблокирован, запрашиваем email
    if status_key in ["key_free", "blocked"]:
        await request_user_email(chat_id, bot, state)
        await state.set_state(PaymentForm.awaiting_email)
    elif status_key == "active":
        expire_key_after_payment = us.servers[0].date_expire_of_paid_key.get()
        await bot.send_message(chat_id, text=f"Ваша подписка активна до *{expire_key_after_payment}*")
    else:
        await bot.send_message(chat_id, text="Оплата скоро будет доступна.")

    # Подтверждаем callback_query
    await callback_query.answer()


# 3. Валидация email
@router.message(PaymentForm.awaiting_email)
async def handle_email_input(message: types.Message, state: FSMContext):
    email = message.text
    chat_id = message.chat.id
    bot = message.bot

    # await save_user_email_to_db(chat_id,email)

    # Валидация email
    if validate_email(email):
        # Загружаем пользователя и записываем email
        us = await UserCl.load_user(chat_id)
        await us.email.set(email)
        user_login = await us.user_login.get()
        # Сохраняем email во временном состоянии FSM
        await state.update_data(email=email)
        one_time_id, one_time_link = await create_one_time_payment(chat_id, user_login, email)

        # Отправляем сообщение с подтверждением email
        text = (f"Вы подключаете подписку на наш сервис с помощью\n"
                "платёжной системы Юkassa\n\n"
                "Стоимость подписки на 1 месяц: 199р 👇👇👇\n\n"
                f"Чек об оплате придет на почту {email}\n\n"
                f"ID платежа {one_time_id}")

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"Оплатить через Юкассу", url=one_time_link)],  # Кнопка "Да" на отдельной строке
                [  # Кнопки "Изменить почту" и "Отменить платеж" на одной строке
                    InlineKeyboardButton(text="Изменить почту", callback_data="edit_email"),
                    InlineKeyboardButton(text="Отменить платеж", callback_data="cancel_payment")
                ]
            ]
        )

        # Пользователь подтвердил email



        sent_message = await bot.send_message(chat_id, text=text, reply_markup=keyboard)
        # Сбрасываем состояние
        await state.clear()


    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"Отменить платеж", callback_data="cancel_payment")]])
        # Сообщаем о неверном формате и просим ввести повторно
        send_message = await bot.send_message(chat_id, "Неверный формат email. Пожалуйста, введите корректный email.",
                                              reply_markup=keyboard)



@router.callback_query(lambda c: c.data in ["confirm_email", "edit_email"])
async def handle_email_confirmation(callback_query: types.CallbackQuery, state: FSMContext):
    chat_id = callback_query.message.chat.id
    bot = callback_query.message.bot
    data = await state.get_data()
    email = data.get("email")



    if callback_query.data == "confirm_email":
        pass
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

    await state.clear()  # Завершаем любое текущее состояние

    await bot.send_message(chat_id, "Платеж был отменен.")

    await callback_query.answer()


