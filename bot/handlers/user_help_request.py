from aiogram import Router, types
from aiogram.types import Message

router = Router()

# ID администратора
ADMIN_CHAT_ID = 456717505

@router.message(lambda message: message.text == "У меня не получается")
async def handle_reply_button(message: Message):
    # Отправляем сообщение пользователю
    await message.answer("Попытаемся объяснить поподробнее, ожидайте обратной связи 😊")

    # Проверка на наличие username, если его нет, используем chat_id
    user_identifier = message.from_user.username or f"ID: {message.from_user.id}"

    # Формируем сообщение для администратора
    admin_message = f"Пользователь {user_identifier} нажал кнопку 'У меня не получается'"

    # Отправляем сообщение администратору
    await message.bot.send_message(ADMIN_CHAT_ID, admin_message)
