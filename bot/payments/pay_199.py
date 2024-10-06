from yookassa import Payment, Configuration
from aiogram import Router, types
from aiogram import Router, types

from aiogram.types import CallbackQuery, LabeledPrice, PreCheckoutQuery
import os

from bot.handlers.cleanup import store_message, register_message_type, delete_unimportant_messages
from bot.payments.add_payment_db import update_has_paid_subscription_db, check_has_paid_subscription_db, \
    test_update_tolsemenovv_has_paid_subscription_db

router = Router()



# Вставьте ваши данные для YooKassa и Telegram
SHOP_ID = os.getenv('SHOPID')
SECRET_KEY = os.getenv('API')
BOT_PAYMENT_TOKEN = os.getenv('PROVIDER_TOKEN_TEST')  # Тестовый токен провайдера

# Настройка конфигурации YooKassa
Configuration.account_id = SHOP_ID
Configuration.secret_key = SECRET_KEY


router = Router()


@router.callback_query(lambda c: c.data == 'payment_199')
async def process_callback_query(callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id  # Получаем chat_id пользователя
    print("Пользователь хочет оплатить")
    # Отправляем сообщение пользователю
    await callback_query.message.bot.send_message(chat_id, "Оплата будет доступна позже")

    # Закрываем callback, чтобы Telegram не показывал "крутящийся" значок ожидания
    await callback_query.answer()
# @router.callback_query(lambda c: c.data == 'payment_199')
# async def process_callback_query(callback_query: types.CallbackQuery):
#     chat_id = callback_query.message.chat.id
#     user_id = callback_query.message.from_user.id
#     bot = callback_query.message.bot
#
#
#     await test_update_tolsemenovv_has_paid_subscription_db(0)
#
#     newcheck = await check_has_paid_subscription_db(chat_id)
#
#     print("newcheck = ", newcheck)
#     check = await check_has_paid_subscription_db(chat_id)
#     if check:
#         share_message = ("У вас тариф уже оплачен! Повторная оплата будет 12.12.24")
#         sent_message = await callback_query.message.answer(share_message, parse_mode="Markdown")
#
#         # Регистрируем тип сообщения для маппинга, чтобы можно было его удалять
#         if sent_message:
#             await store_message(chat_id, sent_message.message_id, share_message, 'bot')
#             await register_message_type(chat_id, sent_message.message_id, 'confirm_payment','bot')  # Оставляем await, т.к. функция асинхронная
#         else:
#             print("Ошибка отправки сообщения: message.answer вернул None")
#         await callback_query.answer()
#         return
#
#     prices = [LabeledPrice(label="Оплата подписки", amount=199 * 100)]  # 199 руб.
#     invoice_message = await callback_query.bot.send_invoice(
#         chat_id=callback_query.from_user.id,
#         title="Оплата подписки",
#         description="Оплата за доступ на месяц",
#         payload="subscription-199",  # Уникальный идентификатор платежа
#         provider_token=BOT_PAYMENT_TOKEN,  # Тестовый токен для Telegram Payments
#         currency="RUB",
#         prices=prices,
#         need_email=True,
#         start_parameter="subscription-payment"
#     )
#
#     # Сохраняем сообщение с платёжной формой
#     await store_message(callback_query.from_user.id, invoice_message.message_id, "Инвойс на оплату", 'bot')
#     await callback_query.answer()


# @router.pre_checkout_query()
# async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
#     await pre_checkout_query.bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

#
# @router.message()
# async def process_successful_payment(message: types.Message):
#
#
#
#     if message.successful_payment:
#         await update_has_paid_subscription_db(1, message.chat.id)
#         # Логируем информацию о платеже
#         successful_payment_info = message.successful_payment
#         print(f"Платеж успешно завершен! Invoice payload: {successful_payment_info.invoice_payload}")
#         print(f"Telegram Payment Charge ID: {successful_payment_info.telegram_payment_charge_id}")
#         print(f"Provider Payment Charge ID: {successful_payment_info.provider_payment_charge_id}")
#
#         # Отправляем пользователю сообщение об успешной оплате
#         await message.answer("Оплата успешно выполнена! Спасибо за покупку.")

