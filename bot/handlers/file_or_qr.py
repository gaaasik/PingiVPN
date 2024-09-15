# Это файл handlers/file_or_qr.py
import os
from aiogram import Router, types
from aiogram.types import CallbackQuery, FSInputFile
from dotenv import load_dotenv

from bot.handlers.cleanup import store_important_message, delete_unimportant_messages
from bot.utils.file_sender import send_config_file, send_qr_code

router = Router()
load_dotenv()
REGISTERED_USERS_DIR = os.getenv("REGISTERED_USERS_DIR")
# Обработчик для конфигурационного файла
# Обработчик для конфигурационного файла
@router.callback_query(lambda c: c.data == "get_config")
async def handle_get_config(callback_query: CallbackQuery):
    await delete_unimportant_messages(callback_query.message.chat.id, callback_query.bot)

    # Отправляем конфигурационный файл и проверяем, что message не None
    message = await send_config_file(callback_query)
    if message:  # Проверка, что файл был отправлен
        await store_important_message(callback_query.bot, callback_query.message.chat.id, message.message_id, message,
                                      message_type="config")

    await callback_query.answer()


# Обработчик для QR-кода
@router.callback_query(lambda c: c.data == "get_qr_code")
async def handle_get_qr_code(callback_query: CallbackQuery):
    await delete_unimportant_messages(callback_query.message.chat.id, callback_query.bot)

    # Отправляем QR-код и проверяем, что message не None
    message = await send_qr_code(callback_query)
    if message:  # Проверка, что файл был отправлен
        await store_important_message(callback_query.bot, callback_query.message.chat.id, message.message_id, message,
                                      message_type="qr_code")

    await callback_query.answer()