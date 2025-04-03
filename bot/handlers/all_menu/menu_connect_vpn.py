# bot/handlers/show_qr.py
from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from bot.handlers.admin import send_admin_log
from bot.handlers.start import check_user_agreement, request_user_agreement
from bot.keyboards.inline import device_choice_keyboard

router = Router()

connect_text_messages = (

    "🌐 Узнайте, что такое настоящее VPN подключение\n\n"
    "🚀 Ваша скорость ограничена только вашим провайдером!\n\n "

    "🔐 Гарантируем защиту ваших данных \n\n"

    "📱 *Выберите устройство для настройки VPN*"
)


@router.callback_query(lambda c: c.data == "connect_vpn")
async def handle_buy_vpn(callback_query: CallbackQuery):
    """Обработчик нажатия кнопки 'Подключиться к VPN'."""

    bot = callback_query.bot
    chat_id = callback_query.from_user.id  # <-- исправлено!

    # Проверяем, принял ли пользователь соглашение
    has_accepted = await check_user_agreement(chat_id)

    if not has_accepted:
        await request_user_agreement(bot, chat_id)  # Если не принято, отправляем запрос на принятие
    else:
        await bot.send_message(  # <-- Используем bot.send_message, а не message.answer
            chat_id,
            connect_text_messages,
            reply_markup=device_choice_keyboard(),
            parse_mode="Markdown"
        )

    await callback_query.answer()

