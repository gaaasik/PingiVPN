
# bot/handlers/show_qr.py
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from bot.handlers.cleanup import store_message, delete_unimportant_messages, store_important_message

import os

from models.UserCl import UserCl

router = Router()

def keyboard_one_key():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Оплатить ключ", callback_data="buy_vpn")],  # Ведет на ссылку для скачивания
        [InlineKeyboardButton(text="Добавить ключ", callback_data="add_key")]
    ])
    return keyboard

def keyboard_without_key():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить ключ", callback_data="connect_vpn")]
    ])
    return keyboard


@router.callback_query(lambda c: c.data == "add_key")
async def handle_add_key(callback_query: CallbackQuery):
    await callback_query.answer("Пока доступен только один ключ")

    await callback_query.answer()



@router.callback_query(lambda c: c.data == "my_keys")
async def handle_my_keys(callback_query: CallbackQuery):
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
        keyboard = keyboard_one_key()
        text_count = "1 ключ"
        text_key_name = await us.servers[0].email_key.get()
        text_country_key = await us.servers[0].country_server.get()
        text_status = await us.servers[0].status_key.get()
        text_url = await us.servers[0].url_vless.get()
        if await us.servers[0].status_key.get() == "free_key":
            text_status = "пробный период"
            text_day_activ = f"Пробный период активен до: {await us.servers[0].date_key_off.get_date()}\n\n"
        elif await us.servers[0].status_key.get() == "activ":
            text_status = "ключ активен"
            text_day_activ = f"Пробный период активен до: {await us.servers[0].date_key_off.get_date()}\n\n"
        else:
            text_status = "ожидание платежа"
            text_day_activ = "Для работы ключа требуется оплата"

    else:
        text_count = "0 ключей"
        keyboard = keyboard_without_key()




    text = (
        f"У вас есть: {text_count}\n"
        f"Ваш ключ: {text_key_name}\n"
        f"Страна сервера: {text_country_key}\n"
        f"Cтатус: {text_status}\n"
        f"{text_day_activ}\n"
        f"{text_traffic}\n"
        f"```\n{text_url}\n```"
        #"При оплате вы продлите срок активного ключа еще на *30 дней*"

    )


    await callback_query.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback_query.answer()






