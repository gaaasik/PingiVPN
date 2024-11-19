# Это файл handlers/file_or_qr.py
import os

from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv


from bot.handlers.cleanup import store_important_message
from bot.keyboards.inline import get_detailed_instruction_button, get_file_button, \
    get_qr_code_button
from bot.utils.file_sender import send_config_file, send_qr_code, send_instruction_video
from bot.utils.subscription_check import check_subscription_channel

router = Router()
load_dotenv()
REGISTERED_USERS_DIR = os.getenv("REGISTERED_USERS_DIR")


# Обработчик для конфигурационного файла
# Обработчик для конфигурационного файла
@router.callback_query(lambda c: c.data == "get_config")
async def handle_get_file(callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
    await send_instruction_video(callback_query)
    # Если подписка подтверждена, отправляем файл
    await send_config_file(callback_query)
    # Отправляем сообщение после отправки файла с двумя кнопками: "Подробная инструкция" и "Показать QR-код"
    await callback_query.message.answer(
        "Загрузите конфигурацию в приложение WireGuard 📂",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [get_detailed_instruction_button()],
            [get_qr_code_button()], [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
    )

    await callback_query.answer()



@router.callback_query(lambda c: c.data == "get_qr_code")
async def handle_get_qr_code(callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id



    # Если подписка подтверждена, отправляем QR-код
    await send_qr_code(callback_query)
    # Отправляем сообщение после отправки QR-кода с двумя кнопками: "Подробная инструкция" и "Получить файл"
    await callback_query.message.answer(
        "Откройте QR-код на другом устройстве и отсканируйте его в приложении 📱",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [get_detailed_instruction_button()],
            [get_file_button()],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
    )

    await callback_query.answer()


