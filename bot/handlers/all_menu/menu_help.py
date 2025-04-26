# bot/handlers/help_menu.py

from aiogram import Router, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from telebot.formatting import escape_markdown

from bot.handlers.admin import ADMIN_CHAT_IDS
from communication_with_servers.test_send_vless_api.send_test import test_toggle_vpn_user
from models.UserCl import UserCl
from work_user_api.ReadyWorkApiServer import ReadyWorkApiServer

router = Router()

# Текст для помощи
help_text_message = (
    f"📚 *Помощь и поддержка*\n"
    f"{escape_markdown('Напишите нам @pingi_help и мы обязательно вам поможем и поддержим:')}"
)

# Клавиатура с вариантами вопросов
def help_options_keyboard():
    buttons = [
        [
            InlineKeyboardButton(
                text="💬 Задать вопрос",
                url="https://t.me/pingi_help"  # Ссылка на чат с админами
            ),
        ],[
            InlineKeyboardButton(text="✍️ Оставить отзыв", callback_data="leave_feedback")
        ],
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Универсальный обработчик для команды "/support" и кнопки "help"
@router.message(Command("support"))
@router.callback_query(F.data == "help")
async def handle_support(event: types.Message | types.CallbackQuery):
    ################################### TEST TOL ######################################################## Задача добавлена в очередь
    chat_id = event.message.chat.id
    us = await UserCl.load_user(chat_id)

    if chat_id in ADMIN_CHAT_IDS:

        server_ip = await us.active_server.server_ip.get()
        email_key = await us.active_server.email_key.get()
        processor = ReadyWorkApiServer(server_ip)

        await processor.process_change_enable_user(email_key=email_key, enable=True, chat_id=chat_id)




    ################################### TEST TOL ######################################################## успешно удален из списка и базы данных.

    if isinstance(event, types.Message):
        await event.answer(help_text_message, reply_markup=help_options_keyboard(), parse_mode="Markdown")
    elif isinstance(event, types.CallbackQuery):
        await event.message.edit_text(help_text_message, reply_markup=help_options_keyboard(), parse_mode="Markdown")
        await event.answer()  # Подтверждаем callback_query