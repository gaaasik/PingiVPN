import asyncio
import logging
import re
from aiogram import Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from models.UserCl import UserCl
from bot.payments2.payments_handler_redis import create_one_time_payment

# Инициализация логирования
logging.basicConfig(level=logging.INFO)

# Инициализация роутера
router = Router()

# Состояние для ввода email
class PaymentForm(StatesGroup):
    awaiting_email = State()

# Функция валидации email
def validate_email(email) -> bool:
    # Если email None или не является строкой, возвращаем False
    if not isinstance(email, str):
        return False
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w{2,4}$"
    return bool(re.match(pattern, email))

# Функция запроса email
async def request_user_email(chat_id: int, bot: Bot, state: FSMContext):
    try:
        text = "Пожалуйста, введите ваш email для отправки чека:"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Отменить платеж", callback_data="cancel_payment")]
            ]
        )
        sent_message = await bot.send_message(chat_id, text=text, reply_markup=keyboard)
        logging.info(f"Отправлен запрос email пользователю: chat_id={chat_id}")

    except Exception as e:
        logging.error(f"Ошибка при запросе email у пользователя: {e}")

# Функция отправки ссылки на оплату
async def send_payment_link(chat_id: int, bot: Bot, user_login: str, email: str, state: FSMContext):
    try:
        one_time_id, one_time_link = await create_one_time_payment(chat_id, user_login, email)
        text = (
            f"Вы подключаете подписку на наш сервис с помощью\n"
            "платёжной системы Юkassa\n\n"
            "Стоимость подписки на 1 месяц: 199₽ 👇👇👇\n\n"
            f"Чек об оплате придет на почту {email}\n\n"

        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Оплатить через Юкассу", url=one_time_link)],
                [
                    InlineKeyboardButton(text="Изменить почту", callback_data="edit_email"),
                    InlineKeyboardButton(text="Отменить платеж", callback_data="cancel_payment")
                ]
            ]
        )
        await bot.send_message(chat_id, text=text, reply_markup=keyboard)
        logging.info(f"Отправлена ссылка на оплату пользователю: chat_id={chat_id}")

        # Сбрасываем состояние FSM
        await state.clear()
    except Exception as e:
        logging.error(f"Ошибка при отправке ссылки на оплату: {e}")
        await bot.send_message(chat_id, "Произошла ошибка при создании платежа. Пожалуйста, попробуйте позже.")

# Основной обработчик при нажатии на кнопку "Оплатить 199 рублей"
@router.callback_query(lambda c: c.data == 'payment_199')
async def handle_payment_request(callback_query: types.CallbackQuery, state: FSMContext):
    chat_id = callback_query.message.chat.id
    bot = callback_query.message.bot

    try:
        # Загружаем пользователя и проверяем статус подписки
        us = await UserCl.load_user(chat_id)
        if not us:
            logging.error(f"Ошибка загрузки данных пользователя: chat_id={chat_id}")
            await bot.send_message(chat_id, "Ошибка загрузки данных пользователя.")
            await callback_query.answer()
            return

        # Проверка, есть ли у пользователя ключ
        if await us.count_key.get() == 0:
            await bot.send_message(chat_id, "У вас нет ключа для оплаты, добавьте ключ.")
            await callback_query.answer()
            return

        # Проверка email пользователя
        user_email = await us.email.get()
        if user_email is None or not validate_email(user_email):
            logging.info(f"Запрос email у пользователя: chat_id={chat_id}")
            await request_user_email(chat_id, bot, state)  # Запрашиваем email, если он отсутствует или не валиден
            await state.set_state(PaymentForm.awaiting_email)
        else:
            user_login = await us.user_login.get()
            await send_payment_link(chat_id, bot, user_login, user_email, state)

    except Exception as e:
        logging.error(f"Ошибка в обработчике handle_payment_request: {e}")
        await bot.send_message(chat_id, "Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.")
    finally:
        # Подтверждаем callback_query
        await callback_query.answer()


# Обработчик ввода email
@router.message(PaymentForm.awaiting_email)
async def handle_email_input(message: types.Message, state: FSMContext):
    email = message.text
    chat_id = message.chat.id
    bot = message.bot

    if validate_email(email):
        try:
            us = await UserCl.load_user(chat_id)
            await us.email.set(email)
            user_login = await us.user_login.get()
            await send_payment_link(chat_id, bot, user_login, email, state)
        except Exception as e:
            logging.error(f"Ошибка при сохранении email: {e}")
            await bot.send_message(chat_id, "Произошла ошибка при сохранении email. Пожалуйста, попробуйте позже.")
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Отменить платеж", callback_data="cancel_payment")]]
        )
        await bot.send_message(chat_id, "Неверный формат email. Пожалуйста, введите корректный email.", reply_markup=keyboard)

# Обработчик подтверждения или изменения email
@router.callback_query(lambda c: c.data in ["confirm_email", "edit_email"])
async def handle_email_confirmation(callback_query: types.CallbackQuery, state: FSMContext):
    chat_id = callback_query.message.chat.id
    bot = callback_query.message.bot
    data = await state.get_data()
    email = data.get("email")

    if callback_query.data == "confirm_email":
        logging.info(f"Пользователь подтвердил email: {email}")
    elif callback_query.data == "edit_email":
        await request_user_email(chat_id, bot, state)
        await state.set_state(PaymentForm.awaiting_email)

    await callback_query.answer()

# Таймер для сброса состояния email через 1 час
async def start_email_timeout(chat_id: int, state: FSMContext, timeout: int = 3600):
    await asyncio.sleep(timeout)
    if await state.get_state() == PaymentForm.awaiting_email:
        await state.clear()
        logging.info(f"Состояние ожидания email сброшено для chat_id={chat_id}")
        #await bot.send_message(chat_id, "Время ожидания ввода email истекло. Пожалуйста, начните процесс заново.")

# Обработчик отмены платежа
@router.callback_query(lambda c: c.data == 'cancel_payment')
async def handle_cancel_payment(callback_query: types.CallbackQuery, state: FSMContext):
    chat_id = callback_query.message.chat.id
    bot = callback_query.message.bot

    await state.clear()
    await bot.send_message(chat_id, "Платеж был отменен.")
    logging.info(f"Платеж отменен пользователем: chat_id={chat_id}")

    await callback_query.answer()
