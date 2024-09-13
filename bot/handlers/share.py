# bot/handlers/share.py
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.handlers.cleanup import delete_unimportant_messages, store_message, messages_for_db
import os
name_bot = os.getenv('name_bot')
router = Router()

share_message = (
    "Твой друг тоже заслуживает безопасный интернет! Перешли это сообщение и помоги ему подключиться к нашему VPN-сервису. 🌐🔒🚀"
)
@router.message(Command("share"))
@router.message(lambda message: message.text == "Поделиться с другом!")
async def cmd_share(message: types.Message):
    await store_message(message.chat.id, message.message_id, message.text, 'user')

    # Получаем ID пользователя и чата
    user_id = message.from_user.id
    chat_id = message.chat.id
    bot = message.bot

    # Генерируем реферальную ссылку
    referral_link = f"https://t.me/{name_bot}?start={user_id}"  # Замените 'YourBot' на username вашего бота

    # Создаем инлайн-кнопку с реферальной ссылкой
    share_link_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Поделиться с другом", url=referral_link)]
        ]
    )

    # Удаление всех старых сообщений с тем же текстом
    for msg in messages_for_db:
        if msg['chat_id'] == chat_id and msg['message_text'] == share_message:
            try:
                await bot.delete_message(chat_id, msg['message_id'])
            except Exception as e:
                print(f"Не удалось удалить сообщение {msg['message_id']}: {e}")

    # Отправка нового сообщения с кнопкой
    sent_message = await message.answer(share_message, reply_markup=share_link_button, parse_mode="Markdown")
    await store_message(chat_id, sent_message.message_id, share_message, 'bot')

    # Удаляем неважные сообщения
    await delete_unimportant_messages(chat_id, bot)
