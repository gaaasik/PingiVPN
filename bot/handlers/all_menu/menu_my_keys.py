from aiogram import types, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

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
    await us.servers[0].name_protocol.get()

    if count_key == 0 or not us.servers:
        # Если у пользователя нет ключей
        text = (
            "<b>У вас нет ключей для оплаты.</b>\n"
            "Пожалуйста, создайте ключ."
        )
        keyboard = get_add_key_keyboard()

    else:
        # Получаем данные ключа
        key_name = await us.servers[0].name_key.get()
        country_flag = await us.servers[0].country_server.get_country()
        traffic_limit = "200 Gb / в мес"
        vless_url = await us.servers[0].url_vless.get()

        # Определяем статус и срок действия ключа
        status_text = await get_user_status_text(us)
        keyboard = get_payment_keyboard()

        # if status_key == "free_key":
        #     status_text = "пробный период"
        #     expiration_text = f" {await us.servers[0].date_key_off.get_date()}"
        #     keyboard = get_payment_keyboard()
        #
        # elif status_key == "blocked":
        #     status_text = "заблокирован"
        #     expiration_text = "Для активации ключа требуется оплата."
        #     keyboard = get_payment_keyboard()
        #
        # elif status_key == "active":
        #     status_text = "Активен"
        #     expiration_date= await us.servers[0].date_key_off.get_date()
        #     if expiration_date >2:
        #         expiration_text = f"{expiration_date}"
        #     elif expiration_date > 0 and expiration_date <3:
        #         expiration_text = f"Осталось {expiration_date} день *требуется оплата*"
        #     elif expiration_date<0:
        #         expiration_text = "Требуется оплата"
        #
        #     keyboard = get_payment_keyboard()
        #
        #
        # else:
        #     status_text = "неизвестен"
        #     expiration_text = "Статус ключа не определен. Обратитесь в поддержку."
        #     keyboard = get_add_key_keyboard()
        name_protocol = await us.servers[0].name_protocol.get()
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

##########################################################################
    if chat_id == 13885130421:
        print("tolsemenov SET_ENABLE")
        us.servers[0].enable.set(False)

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
