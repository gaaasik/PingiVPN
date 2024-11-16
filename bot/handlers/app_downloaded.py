from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

router = Router()

# Кнопки для файла, QR-кода и подробной инструкции
def generate_file_or_qr_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Получить файл", callback_data="get_config"),
            InlineKeyboardButton(text="Показать QR-код", callback_data="get_qr_code")
        ],
        [
            InlineKeyboardButton(
                text="Подробная инструкция",
                url="https://telegra.ph/Podrobnaya-instrukciya-po-podklyucheniyu-k-Pingi-VPN-09-17"
            )
        ]
    ])

# Обработчик для кнопки "Я скачал ✅"
@router.callback_query(lambda c: c.data == "app_downloaded")
async def handle_app_downloaded(callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id

    # Текст сообщения
    text = (
        "Импортируйте конфигурационный файл в приложении\n\n"
        "Или отсканируйте QR-код через приложение.\n\n"
        "Для простоты понимания в подробной инструкции описаны все шаги."
    )

    # Отправляем сообщение с клавиатурой
    await callback_query.message.answer(
        text,
        reply_markup=generate_file_or_qr_keyboard()
    )
    await callback_query.answer()
