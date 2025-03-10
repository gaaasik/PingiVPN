# bot/handlers/help_menu.py
import logging

from aiogram import Router, types, Bot, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from telebot.formatting import escape_markdown

from bot.handlers.admin import ADMIN_CHAT_IDS
from models.UserCl import UserCl

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
    print("tolsemenov MENU_MY_KEYS ", chat_id)
    if chat_id in ADMIN_CHAT_IDS:
        us = await UserCl.load_user(chat_id)
        await us.update_key_to_vless()
        # if us.active_server:
        #     print("server_ip = ", await us.active_server.server_ip.get())
        #     for key in us.history_key_list:
        #         key_identifier = await key.uuid_id.get()
        #         if key_identifier == "85ff45f9-c56b-4708-856f-4f778bdf2c3c":
        #             print("country_server ", await key.country_server.get())
        #             print("date_key_off ", await key.date_key_off.get())
        #             print("enable ", await key.enable.get())
        #             print("email_key ", await key.email_key.get())
        #             print("server_ip ", await key.server_ip.get())
        #             await key.enable.set_enable_admin(False)
        #             logging.info(f"TESt_TOL: {key_identifier}, enable=False")
        #             return


    ################################### TEST TOL ######################################################## успешно удален из списка и базы данных.

    if isinstance(event, types.Message):
        await event.answer(help_text_message, reply_markup=help_options_keyboard(), parse_mode="Markdown")
    elif isinstance(event, types.CallbackQuery):
        await event.message.edit_text(help_text_message, reply_markup=help_options_keyboard(), parse_mode="Markdown")
        await event.answer()  # Подтверждаем callback_query