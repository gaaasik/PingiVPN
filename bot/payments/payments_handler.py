# import os
#
# from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
# from dotenv import load_dotenv
# from yookassa import Configuration, Payment
# from aiogram import Router, types
#
# load_dotenv()
# WEBHOOK_URL = os.getenv('WEBHOOK_URL')
#
# # Настройка API Юкассы
# Configuration.account_id = os.getenv('SHOPID')# Ваш shopId
# Configuration.secret_key = os.getenv('API_KEY')  # Ваш секретный ключ API
#
#
#
# router = Router()
#
# @router.callback_query(lambda c: c.data == 'payment_199')
# async def process_callback_query(callback_query: types.CallbackQuery):
#     chat_id = callback_query.message.chat.id
#     user_id = callback_query.message.from_user.id
#     bot = callback_query.message.bot
#
#     # Создаем платёж и получаем ссылку
#     one_time_id, one_time_link, one_time_payment_method_id = create_one_time_payment(user_id)
#
#     # Текст сообщения
#     text_payment = (
#         "Вы подключаете подписку на наш сервис с помощью\n"
#         "платёжной системы Юkassa\n\n"
#         "Стоимость подписки на 1 месяц: 199р 👇👇👇\n"
#     )
#
#     # Создаем клавиатуру с кнопкой
#     keyboard = InlineKeyboardMarkup(
#         inline_keyboard=[
#             [InlineKeyboardButton(text="Оплатить 199р", url=one_time_link)]
#         ]
#     )
#
#     # Отправляем сообщение с текстом и клавиатурой
#     await bot.send_message(
#         chat_id=chat_id,
#         text=text_payment,
#         reply_markup=keyboard
#     )
#     # Подтверждаем callback_query, чтобы избежать зависания
#     await callback_query.answer()
#
#
# # Функция для создания разового платежа
# def create_one_time_payment(user_id):
#     payment = Payment.create({
#         "amount": {
#             "value": "199.00",
#             "currency": "RUB"
#         },
#         "confirmation": {
#             "type": "redirect",
#             "return_url": WEBHOOK_URL
#         },
#         "capture": True,
#         "description": "Подписка на Telegram-бот",
#         "metadata": {
#             "user_id": user_id
#         }
#     })
#     return payment.id, payment.confirmation.confirmation_url, '0'
#
#
