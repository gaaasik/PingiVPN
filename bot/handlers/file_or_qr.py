# Это файл handlers/file_or_qr.py
import os
import re

from aiogram import Router, types
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardMarkup
from dotenv import load_dotenv

from bot.handlers.cleanup import store_important_message, delete_unimportant_messages
from bot.keyboards.inline import subscribe_keyboard, get_detailed_instruction_button, get_file_button, \
    get_qr_code_button
from bot.utils.db import update_user_subscription_status
from bot.utils.file_sender import send_config_file, send_qr_code, send_instruction_video
from bot.utils.subscription_check import should_check_subscription, update_subscription_status, check_subscription
from data.text_messages import detailed_instructions_message

router = Router()
load_dotenv()
REGISTERED_USERS_DIR = os.getenv("REGISTERED_USERS_DIR")


# Обработчик для конфигурационного файла
# Обработчик для конфигурационного файла
@router.callback_query(lambda c: c.data == "get_config")
async def handle_get_file(callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id

    # Проверяем подписку пользователя
    if not await check_subscription(chat_id, callback_query.bot):
        # Отправляем сообщение с кнопками "Перейти на канал" и "Я подписался"
        message = await callback_query.message.answer(
            "VPN работает без рекламы. Чтобы начать пользоваться — подпишитесь на канал PingiVPN.",
            reply_markup=subscribe_keyboard()
        )
        # Сохраняем это сообщение как важное
        await store_important_message(callback_query.bot, chat_id, message.message_id, message, "subscription_check")
        return

    await send_instruction_video(callback_query)
    # Если подписка подтверждена, отправляем файл
    await send_config_file(callback_query)
    # Отправляем сообщение после отправки файла с двумя кнопками: "Подробная инструкция" и "Показать QR-код"
    await callback_query.message.answer(
        "Загрузите конфигурацию в приложение WireGuard 📂",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [get_detailed_instruction_button()],
            [get_qr_code_button()]
        ])
    )

    await callback_query.answer()


# Обработчик для QR-кода
def detailed_instruction_button():
    pass


@router.callback_query(lambda c: c.data == "get_qr_code")
async def handle_get_qr_code(callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id

    # Проверяем подписку пользователя
    if not await check_subscription(chat_id, callback_query.bot):
        # Отправляем сообщение с кнопками "Перейти на канал" и "Я подписался"
        message = await callback_query.message.answer(
            "VPN работает без рекламы. Чтобы начать пользоваться — подпишитесь на канал PingiVPN.",
            reply_markup=subscribe_keyboard()
        )
        # Сохраняем это сообщение как важное
        await store_important_message(callback_query.bot, chat_id, message.message_id, message, "subscription_check")
        return

    # Если подписка подтверждена, отправляем QR-код
    await send_qr_code(callback_query)
    # Отправляем сообщение после отправки QR-кода с двумя кнопками: "Подробная инструкция" и "Получить файл"
    await callback_query.message.answer(
        "Откройте QR-код на другом устройстве и отсканируйте его в приложении 📱",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [get_detailed_instruction_button()],
            [get_file_button()]
        ])
    )

    await callback_query.answer()


async def handle_get_file(callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id

    # Проверяем подписку пользователя
    if not await check_subscription(chat_id, callback_query.bot):
        # Отправляем сообщение с кнопками "Перейти на канал" и "Я подписался"
        message = await callback_query.message.answer(
            "VPN работает без рекламы. Чтобы начать пользоваться — подпишитесь на канал PingiVPN.",
            reply_markup=subscribe_keyboard()
        )
        # Сохраняем это сообщение как важное
        await store_important_message(callback_query.bot, chat_id, message.message_id, message, "subscription_check")
        return

    # Если подписка подтверждена, отправляем файл
    await send_config_file(callback_query)

    await callback_query.answer()
