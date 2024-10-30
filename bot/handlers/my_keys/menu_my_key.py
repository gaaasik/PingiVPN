
# bot/handlers/show_qr.py
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.types import CallbackQuery

from bot.all_message.text_messages import connect_text_messages
from bot.handlers.cleanup import store_message, delete_unimportant_messages, store_important_message
from bot.keyboards.inline import device_choice_keyboard
import os

router = Router()



@router.callback_query(lambda c: c.data == "my_keys")
async def handle_buy_vpn(callback_query: CallbackQuery):


    sent_message = await callback_query.message.answer(connect_text_messages, reply_markup=device_choice_keyboard(),
                                                       parse_mode="Markdown")




async def generator_menu_my_key(chat_id: int, bot: Bot, status: str, days_since_registration: int):
    # Получаем данные о пользователе по chat_id
    user = await bot.get_chat(chat_id)
    user_name = f"{user.first_name} {user.last_name or ''}".strip()

    # Формирование текста главного меню
    text = (
        f"Привет {user_name}! 🕶\n\n"
        "PingiVPN - быстрый и безопасный доступ к свободному интернету без ограничений\n\n"
        "📱 Доступ к любым социальным сетям\n"
        "🛡 Анонимность\n"
        "📶 Устойчивость к блокировкам\n"
        "🚀 Высокая скорость\n"
        "💻 Поддержка любых устройств\n\n"
        f"🔑 Статус: {status}\n"
        f"🕓 Вы с нами уже {days_since_registration} дней! 🥳\n"
    )