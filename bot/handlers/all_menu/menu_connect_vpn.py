# bot/handlers/show_qr.py
from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from bot.handlers.admin import send_admin_log

router = Router()

connect_text_messages = (

    "🌐 Узнайте, что такое настоящее VPN подключение\n\n"
    "🚀 Ваша скорость ограничена только вашим провайдером!\n\n "

    "🔐 Гарантируем защиту ваших данных \n\n"

    "📱 *Выберите устройство для настройки VPN*"
)




def device_choice_keyboard():
    """Клавиатура для выбора устройства"""

    # Создаем кнопки
    buttons = [
        [
            InlineKeyboardButton(text="🤖 Android", callback_data="device_android"),
            InlineKeyboardButton(text="📱 iPhone", callback_data="device_iPhone")
        ],
        [
            InlineKeyboardButton(text="💻 Mac", callback_data="device_mac"),
            InlineKeyboardButton(text="🐧 Linux", callback_data="device_linux")
        ],
        [
            InlineKeyboardButton(text="🖥️ Windows", callback_data="device_windows")
        ],
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
        ],
    ]
    # Создаем клавиатуру с кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard



@router.callback_query(lambda c: c.data == "connect_vpn")
async def handle_buy_vpn(callback_query: CallbackQuery):


    sent_message = await callback_query.message.answer(connect_text_messages, reply_markup=device_choice_keyboard(),
                                                       parse_mode="Markdown")
    await callback_query.answer()


