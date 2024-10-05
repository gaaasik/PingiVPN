from yookassa import Payment, Configuration
from aiogram import Router, types
from aiogram import Router, types

from aiogram.types import CallbackQuery
from bot.handlers.cleanup import store_message, delete_unimportant_messages, store_important_message
import json
import asyncio
import os
import time
router = Router()



# # Настройка конфигурации YooKassa
Configuration.account_id = os.getenv('SHOPID')
Configuration.secret_key = os.getenv('API_KEY')




# ################################################
user_payments = {}
###################################



#Создание url для перехода по ссылки
def create_payment199(message):
    user_id = message.from_user.id

    payment = Payment.create({
        "amount": {
            "value": "199.00",  # Сумма оплаты
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": os.getenv('URL')  # URL для возврата после оплаты
        },
        "capture": True,
        "description": "Оплата за одписку на месяц 199р"
    })

# ####################################################################### Сохраняем платеж для пользователя
    user_payments[user_id] = payment.id
    check_payment(user_id, payment.id)

    return payment.confirmation.confirmation_url



# def check_payment_status(user_id):
#     if user_id in user_payments:
#         payment_id = user_payments[user_id]
#         payment = Payment.find_one(payment_id)
#         return payment.status
#     return None


def check_payment(user_id, payment_id):
    if user_id in user_payments:
        print("СТАРТ ОБРАБОТЧИКА//////////////////////////////////////////////////////////////////////////")
        payment = Payment.find_one(payment_id)
        start_time = time.time()  # Засекаем время начала
        timeout = 10  # 5 минут в секундах
        while payment['status'] == 'pending':
            print("Платеж в состоянии ожидания//////////////////////////////////////////////////////////////////////////")

            payment = Payment.find_one(payment_id)
            asyncio.sleep(3)
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout:
                print("Время ожидания истекло, прекращаем проверку//////////////////////////////////////////////////////////////////////////")
                # Отправляем сообщение пользователю о таймауте
                # await bot.send_message(user_id, "Время ожидания оплаты истекло. Попробуйте снова.")
                return False


        print("Обработчик закончился//////////////////////////////////////////////////////////////////////////")
        if payment['status'] == 'succeeded':
            print("SUCCSESS RETURN")
            #await message.answer("оплата прошла")
            #await bot.send_message(chat_id, "Добро пожаловать!")
            print(payment)
            return True
        else:
            print("BAD RETURN")
            #await message.answer("оплата НЕ прошла")
            print(payment)
            return False

	# payment = json.loads((Payment.find_one(payment_id)).json())
	# while payment['status'] == 'pending':
	# 	payment = json.loads((Payment.find_one(payment_id)).json())
	# 	await asyncio.sleep(3)
    #
	# if payment['status']=='succeeded':
	# 	print("SUCCSESS RETURN")
	# 	print(payment)
	# 	return True
	# else:
	# 	print("BAD RETURN")
	# 	print(payment)
	# 	return False


@router.callback_query(lambda c: c.data.startswith("payment"))
async def handle_device_choice(callback_query: CallbackQuery):
    await delete_unimportant_messages(callback_query.message.chat.id, callback_query.bot)

    message = await callback_query.message.answer("Начали оплату.")

    await store_important_message(callback_query.bot, callback_query.message.chat.id, message.message_id, message,
                                  message_type="device_choice")

    await callback_query.answer()




