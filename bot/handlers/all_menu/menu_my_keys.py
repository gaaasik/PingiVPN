
# bot/handlers/show_qr.py
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.types import CallbackQuery


from bot.handlers.cleanup import store_message, delete_unimportant_messages, store_important_message

import os

from models.UserCl import UserCl

router = Router()



@router.callback_query(lambda c: c.data == "my_keys")
async def handle_buy_vpn(callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
    us = await UserCl.load_user(chat_id)
    text_count = "0 ключей"
    text_key_name = ""
    text_country_key = ""
    text_status = ""
    text_day_activ = ""
    text_traffic = "Трафик: 200Gb в/мес"
    text_url = ""

    if await us.count_key.get() > 0:
        text_count = "1 ключ"
        text_key_name = await us.servers[0].name_key_for_user.get()
        text_country_key = await us.servers[0].country_server.get()
        text_status = us.servers[0].status_key.get()
        text_url = us.servers[0].url_vless
        if us.servers[0].status_key.get() == "free_key":
            text_status = "пробный период"
            text_day_activ = f"Пробный период активен до: {us.servers[0].date_key_off.get_date()}\n\n"
        elif us.servers[0].status_key.get() == "activ":
            text_status = "ключ активен"
            text_day_activ = f"Пробный период активен до: {us.servers[0].date_key_off.get_date()}\n\n"
        else:
            text_status = "ожидание платежа"
            text_day_activ = "Для работы ключа требуется оплата"

    else:
        text_count = "0 ключей"




    text = (
        f"У вас есть: {text_count}\n"
        f"Ваш ключ: {text_key_name}\n"
        f"Страна сервера: {text_country_key}\n"
        f"Cтатус: {text_status}\n"
        f"{text_day_activ}\n"
        f"{text_traffic}\n"
        f"```\n{text_url}\n```"
        "При оплате вы продлите срок активного ключа еще на *30 дней*"

    )


    await callback_query.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback_query.answer()






async def show_menu_my_key(chat_id: int, bot: Bot, status: str, days_since_registration: int):
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