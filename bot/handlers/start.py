# bot/handlers/start.py
import os

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from bot.handlers.cleanup import store_message, store_important_message
from bot.keyboards.reply import reply_keyboard
from bot.utils.db import add_user, drop_table, get_user_by_telegram_id, add_referral
from bot.utils.file_manager import send_files_to_user
from data.text_messages import instructions_message, welcome_message

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):

    # Проверяем, есть ли аргументы в команде /start
    if len(message.text.split()) > 1:
        args = message.text.split()[1]  # Аргумент передается после команды /start
    else:
        args = None  # Если аргументов нет
    # Сохраняем сообщение в базе данных
    await store_message(message.chat.id, message.message_id, message.text, 'user')

    # Получаем ID чата и никнейм пользователя
    chat_id = message.chat.id
    username = message.from_user.username or "unknown"
    # Отправляем приветственное сообщение
    sent_message = await message.answer(welcome_message, reply_markup=reply_keyboard)
    await store_important_message(message.chat.id, sent_message.message_id, sent_message)

    # Формируем название папки как "id чата_никнейм пользователя"
    folder_name = f"{chat_id}_{username}"

    # Проверяем, если пользователь существует в базе данных
    user = await get_user_by_telegram_id(message.from_user.id)
    # Если это новый пользователь, регистрируем его
    referrer_id = int(args) if args else None  # Если есть реферальный код, используем его

    # Проверяем, зарегистрирован ли пользователь
    if not user:
           # Если это новый пользователь, регистрируем его
            await add_user(
                chat_id=message.from_user.id,
                user_name=message.from_user.username or message.from_user.first_name,
                referrer_id=referrer_id  # Сохраняем ID пригласившего пользователя
            )
            # Отправляем уведомление в чат 456717505
            await message.bot.send_message(
                chat_id=456717505,  # ID чата для уведомления
                text=f"Добавлен новый пользователь: {username} (ID чата: {chat_id})"
            )

    # Если есть пригласивший, сохраняем эту информацию
    if referrer_id:
        await add_referral(referrer_id, message.from_user.id)

    # Отправка файлов пользователю
    await send_files_to_user(message, folder_name, use_existing=False)
