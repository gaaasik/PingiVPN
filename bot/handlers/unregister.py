# bot/handlers/start.py
from aiogram import Router, types, Bot
from aiogram.filters import Command

from bot.handlers.cleanup import store_message, clear_chat_history
from bot.database.db import get_user_by_telegram_id


router = Router()
@router.message(Command("unregister"))
async def cmd_unregister(message: types.Message, bot: Bot):
    # Сохраняем сообщение пользователя
    await store_message(message.chat.id, message.message_id, message.text, 'user')

    user = await get_user_by_telegram_id(message.from_user.id)

    if user:
        unregister_message = await message.answer(
            "😢 Мы будем скучать по вам! Ваша регистрация была удалена, но вы всегда можете вернуться. Просто нажмите /start, когда захотите снова стать частью нашего безопасного сообщества! 🔒"
        )
        # Сохраняем сообщение о снятии регистрации
        await store_message(message.chat.id, unregister_message.message_id, unregister_message.text, 'bot')
    else:
        unregister_message = await message.answer("Вы не зарегистрированы.")
        # Сохраняем сообщение о том, что пользователь не зарегистрирован
        await store_message(message.chat.id, unregister_message.message_id, unregister_message.text, 'bot')

    # Удаление команды /unregister и сообщения бота
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    await bot.delete_message(chat_id=message.chat.id, message_id=unregister_message.message_id)

    # Удаление всех сообщений в чате
    await clear_chat_history(message.chat.id, bot)