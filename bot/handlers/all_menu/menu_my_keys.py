from aiogram import types, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from bot.handlers.admin import ADMIN_CHAT_IDS
from bot.handlers.all_menu.main_menu import get_user_status_text
from bot.handlers.all_menu.menu_buy_vpn import get_add_key_keyboard

from models.UserCl import UserCl
import logging

router = Router()


# Вспомогательные функции для клавиатур
def get_payment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить ключ", callback_data="buy_vpn")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ]
    )


def keyboard_without_key():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить ключ", callback_data="connect_vpn")]
        ]
    )

import logging

def escape_markdown(text: str) -> str:
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '!']
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text


async def generate_key_status_text(us: UserCl) -> (str, InlineKeyboardMarkup):
    """
    Генерирует текст сообщения о состоянии ключа пользователя и возвращает его вместе с клавиатурой.
    """
    count_key = await us.count_key.get()
    active_server = us.active_server



    if count_key == 0 or not active_server:
        # Если у пользователя нет ключей
        text = (
            "<b>У вас нет ключей для оплаты.</b>\n"
            "Пожалуйста, создайте ключ."
        )
        keyboard = get_add_key_keyboard()

    else:
        # Получаем данные ключа
        name_key = await us.active_server.name_key.get()
        country_flag = await us.active_server.country_server.get_country()
        traffic_limit = "200 Gb / в мес"
        vless_url = await us.active_server.url_vless.get()

        # Определяем статус и срок действия ключа
        status_text = await get_user_status_text(us)
        keyboard = get_payment_keyboard()

        name_protocol = await us.active_server.name_protocol.get()
        if name_protocol == "wireguard":
            # Формируем текст сообщения в формате HTML
            text = (
                f"🔐 <b>Ваш VPN-ключ:</b>\n\n"
                f"- <b>Имя ключа</b>: {name_key}\n"
                f"- <b>Страна сервера</b>: {country_flag}\n"
                f"- <b>Статус</b>: <b>{status_text}</b>\n"
                #f"- <b>Действителен до</b>: <b>{expiration_text}</b>\n\n"
                f"🌐 <b>Лимит трафика</b>: {traffic_limit}\n\n"
            )
        else:

            # Формируем текст сообщения в формате HTML
            text = (
                f"🔐 <b>Ваш VPN-ключ:</b>\n\n"
                f"- <b>Имя ключа</b>: {name_key}\n"
                f"- <b>Страна сервера</b>: {country_flag}\n"
                f"- <b>Статус</b>: {status_text}\n"
                #f"- <b>Действителен до</b>: <b>{expiration_text}</b>\n\n"
                f"🌐 <b>Лимит трафика</b>: {traffic_limit}\n\n"
                f"<b>Ссылка для подключения:</b>\n"
                f"<pre>{vless_url}</pre>"
            )

    return text, keyboard

@router.callback_query(lambda c: c.data == "my_keys")
async def handle_my_keys(callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
    us = await UserCl.load_user(chat_id)

####################################TEST#####################################
    # print("tolsemenov MENU_MY_KEYS ", chat_id)
    if chat_id in ADMIN_CHAT_IDS:
        us = await UserCl.load_user(1388513042)
        if us.active_server:
            print("server_ip = ", await us.active_server.server_ip.get())
            print("enable = ", await us.active_server.enable.get())
            print("name_protocol = ", await us.active_server.name_protocol.get())
            await us.active_server.enable.set(False)

###########################################################################
    try:
        # Генерируем текст и клавиатуру для ответа
        text, keyboard = await generate_key_status_text(us)

        # Отправляем сообщение
        await callback_query.message.answer(text, reply_markup=keyboard, disable_web_page_preview=True,
                                            parse_mode="HTML")

    except Exception as e:
        logging.error(f"Ошибка при генерации сообщения о ключах: {e}")
        await callback_query.message.answer("Произошла ошибка при проверке статуса. Попробуйте позже.")

    await callback_query.answer()
