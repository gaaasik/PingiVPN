import os

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
from yookassa import Configuration, Payment
from aiogram import Router, types

from bot.handlers.admin import send_admin_log

load_dotenv()
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Настройка API Юкассы
Configuration.account_id = os.getenv('SHOPID')# Ваш shopId
Configuration.secret_key = os.getenv('API_KEY')  # Ваш секретный ключ API



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


