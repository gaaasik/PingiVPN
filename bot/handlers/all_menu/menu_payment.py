import asyncio
import logging
import re
from aiogram import Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.handlers.admin import send_admin_log
from bot.handlers.all_menu.main_menu import show_main_menu
from bot.handlers.all_menu.menu_buy_vpn import TARIFFS
from models.UserCl import UserCl
from bot.payments2.payments_handler_redis import create_one_time_payment
#import dns.resolver
# Инициализация логирования
logging.basicConfig(level=logging.INFO)

# Инициализация роутера
router = Router()

# Состояние для ввода email
class PaymentForm(StatesGroup):
    awaiting_email = State()

# Функция валидации email

def validate_email(email: str) -> bool:
    """
    Проверяет, является ли email корректным с точки зрения синтаксиса.
    :param email: Email-адрес для проверки.
    :return: True, если email-адрес корректен, иначе False.
    """
    if not isinstance(email, str):
        return False

    # Регулярное выражение для проверки синтаксиса email
    pattern = r"^(?!.*\.\.)(?!.*\.$)(?!.*@.*@)[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"

    # Синтаксическая проверка с использованием регулярного выражения
    return bool(re.match(pattern, email))

# Функция запроса email
async def request_user_email(chat_id: int, bot: Bot, state: FSMContext):
    try:
        text = "Пожалуйста, введите ваш email для отправки чека:"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отменить платеж", callback_data="cancel_payment")]
            ]
        )
        sent_message = await bot.send_message(chat_id, text=text, reply_markup=keyboard)
        logging.info(f"Отправлен запрос email пользователю: chat_id={chat_id}")

    except Exception as e:
        logging.error(f"Ошибка при запросе email у пользователя: {e}")


async def send_payment_link(chat_id: int, bot: Bot, user_login: str, email: str, state: FSMContext, tariff_code: str):
    tariff = TARIFFS.get(tariff_code)
    if not tariff:
        await bot.send_message(chat_id, "❌ Неверный тариф.")
        return

    try:
        # Генерация платёжной ссылки
        one_time_id, one_time_link = await create_one_time_payment(chat_id, user_login, email, tariff_code)

        # Текст сообщения
        text = (
            f"🛡 *Оформление подписки через ЮKassa*\n\n"
            f"💵 {tariff['label']}: *{tariff['amount']}₽*\n\n"
            f"📧 Чек отправим на *{email}*\n\n"
            "⬇️ Нажмите кнопку для оплаты ⬇️"
        )

        # Кнопки
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💳 Оплатить через Юкассу", url=one_time_link)],
                [
                    InlineKeyboardButton(text="✏️ Изменить почту", callback_data="edit_email"),
                    InlineKeyboardButton(text="❌ Отменить платеж", callback_data="cancel_payment")
                ]
            ]
        )

        await bot.send_message(chat_id, text=text, reply_markup=keyboard, parse_mode="Markdown")
        logging.info(f"✅ Отправлена ссылка на оплату {tariff_code} пользователю: chat_id={chat_id}")
        await state.clear()

    except Exception as e:
        logging.error(f"Ошибка при создании платежа для {tariff_code}: {e}")
        await bot.send_message(chat_id, "Произошла ошибка при создании платежа. Пожалуйста, попробуйте позже.")


#
# # Функция отправки ссылки на оплату process_payment_message
# async def send_payment_link(chat_id: int, bot: Bot, user_login: str, email: str, state: FSMContext):
#     try:
#         one_time_id, one_time_link = await create_one_time_payment(chat_id, user_login, email)
#         text = (
#             "🛡 *Оформление подписки через ЮKassa*\n\n"
#             "💵 1 месяц: *199₽*\n\n"
#             f"📧 Чек отправим на *{email}*\n\n"
#             "⬇️ Нажмите для оплаты ⬇️"
#         )
#
#         keyboard = InlineKeyboardMarkup(
#             inline_keyboard=[
#                 [InlineKeyboardButton(text="💳 Оплатить через Юкассу", url=one_time_link)],
#                 [
#                     InlineKeyboardButton(text="✏️ Изменить почту", callback_data="edit_email"),
#                     InlineKeyboardButton(text="❌ Отменить платеж", callback_data="cancel_payment")
#                 ]
#             ]
#         )
#         await bot.send_message(chat_id, text=text, reply_markup=keyboard,parse_mode="Markdown")
#         logging.info(f"Отправлена ссылка на оплату пользователю: chat_id={chat_id}")
#
#         # Сбрасываем состояние FSM
#         await state.clear()
#     except Exception as e:
#         logging.error(f"Ошибка при отправке ссылки на оплату: {e}")
#         await bot.send_message(chat_id, "Произошла ошибка при создании платежа. Пожалуйста, попробуйте позже.")

# # Основной обработчик при нажатии на кнопку "Оплатить 199 рублей"
# @router.callback_query(lambda c: c.data == 'payment_199')
# async def handle_payment_request(callback_query: types.CallbackQuery, state: FSMContext):
#     chat_id = callback_query.message.chat.id
#     bot = callback_query.message.bot
#
#     try:
#         # Загружаем пользователя и проверяем статус подписки
#         us = await UserCl.load_user(chat_id)
#         if not us:
#             logging.error(f"Ошибка загрузки данных пользователя: chat_id={chat_id}")
#             await bot.send_message(chat_id, "Ошибка загрузки данных пользователя.")
#             await callback_query.answer()
#             return
#
#         # Проверка, есть ли у пользователя ключ
#         if await us.count_key.get() == 0:
#             await bot.send_message(chat_id, "У вас нет ключа для оплаты, добавьте ключ.")
#             await callback_query.answer()
#             return
#
#         # Проверка email пользователя
#         user_email = await us.email.get()
#         if user_email is None or not validate_email(user_email):
#             logging.info(f"Запрос email у пользователя: chat_id={chat_id}")
#             await request_user_email(chat_id, bot, state)  # Запрашиваем email, если он отсутствует или не валиден
#             await state.set_state(PaymentForm.awaiting_email)
#         else:
#             user_login = await us.user_login.get()
#             await send_payment_link(chat_id, bot, user_login, user_email, state)
#         await send_admin_log(callback_query.bot, f"Пользователь {chat_id} нажал ВТОРУЮ кнопку оплатить")
#
#     except Exception as e:
#         logging.error(f"Ошибка в обработчике handle_payment_request: {e}")
#         await bot.send_message(chat_id, "Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.")
#     finally:
#         # Подтверждаем callback_query
#         await callback_query.answer()


# Обработчик ввода email

@router.callback_query(lambda c: c.data.startswith("payment_plan_"))
async def handle_tariff_payment(callback_query: types.CallbackQuery, state: FSMContext):
    chat_id = callback_query.message.chat.id
    bot = callback_query.message.bot

    tariff_code = callback_query.data.split("_")[-1]  # "1", "3", "6"
    tariff = TARIFFS.get(tariff_code)

    if not tariff:
        await bot.send_message(chat_id, "❌ Неверный тариф.")
        await callback_query.answer()
        return

    try:
        user = await UserCl.load_user(chat_id)
        if not user:
            await bot.send_message(chat_id, "Ошибка: пользователь не найден.")
            await callback_query.answer()
            return

        if await user.count_key.get() == 0:
            await bot.send_message(chat_id, "У вас нет ключа для оплаты. Пожалуйста, сначала подключите VPN.")
            await callback_query.answer()
            return

        user_email = await user.email.get()
        if not user_email or not validate_email(user_email):
            await request_user_email(chat_id, bot, state)
            await state.set_state(PaymentForm.awaiting_email)
            await state.update_data(tariff_code=tariff_code)
        else:
            user_login = await user.user_login.get()
            await send_payment_link(chat_id, bot, user_login, user_email, state, tariff_code)

        await send_admin_log(bot, f"Пользователь {chat_id} выбрал оплату: {tariff['label']}")
        await callback_query.answer()

    except Exception as e:
        logging.error(f"Ошибка в обработчике тарифной оплаты: {e}")
        await bot.send_message(chat_id, "Произошла ошибка. Попробуйте позже.")
        await callback_query.answer()


@router.message(PaymentForm.awaiting_email)
async def handle_email_input(message: types.Message, state: FSMContext):
    email = message.text
    chat_id = message.chat.id
    bot = message.bot
    data = await state.get_data()
    tariff_code = data.get("tariff_code")

    if validate_email(email):
        try:
            us = await UserCl.load_user(chat_id)
            await us.email.set(email)
            user_login = await us.user_login.get()
            await send_payment_link(chat_id, bot, user_login, email, state, tariff_code)
            await send_admin_log(bot, f"Пользователь {chat_id} получил ссылку на оплату, ждем оплаты, подтверждения или отмены")
        except Exception as e:
            logging.error(f"Ошибка при сохранении email: {e}")
            await bot.send_message(chat_id, "Произошла ошибка при сохранении email. Пожалуйста, попробуйте позже.")
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Отменить платеж", callback_data="cancel_payment")]]
        )
        await bot.send_message(chat_id, "Неверный формат email. Пожалуйста, введите корректный email.", reply_markup=keyboard)

@router.callback_query(lambda c: c.data in ["confirm_email", "edit_email"])
async def handle_email_confirmation(callback_query: types.CallbackQuery, state: FSMContext):
    chat_id = callback_query.message.chat.id
    bot = callback_query.message.bot
    data = await state.get_data()
    tariff_code = data.get("tariff_code")
    email = data.get("email")

    if callback_query.data == "confirm_email":
        logging.info(f"Пользователь подтвердил email: {email}")
    elif callback_query.data == "edit_email":
        await request_user_email(chat_id, bot, state)
        await state.set_state(PaymentForm.awaiting_email)
        await state.update_data(tariff_code=tariff_code, email=email)  # сохраняем и тариф, и email обратно в state!

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
    await show_main_menu(chat_id,bot)
    logging.info(f"Платеж отменен пользователем: chat_id={chat_id}")

    await callback_query.answer()
