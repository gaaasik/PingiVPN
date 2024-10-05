from bot.handlers.cleanup import store_message, delete_unimportant_messages
from aiogram import Router, types
router = Router()
@router.callback_query(lambda callback_query: callback_query.data == "pay_199")
async def handle_payment(callback_query: types.CallbackQuery):
    chat_id = callback_query.from_user.id
    bot = callback_query.bot

    # Сообщение об оплате
    payment_message = "Оплата будет доступна в течение трех дней."

    # Отправка сообщения пользователю
    sent_message = await bot.send_message(chat_id, payment_message)

    # Логирование в текстовый файл (чата пользователя)
    await store_message(chat_id, sent_message.message_id, payment_message, 'bot')

    # Удаление старых сообщений о платежах (чтобы не было дубликатов)
    await delete_unimportant_messages(chat_id, bot)

    # Удаление исходного сообщения (нажатие на кнопку)
    await callback_query.message.delete()

    # Уведомление пользователю о результате
    await bot.answer_callback_query(callback_query.id, "Информация об оплате отправлена!")
