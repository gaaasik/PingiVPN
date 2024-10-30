# menu_buy_vpn.py
from aiogram import Router
from aiogram.types import CallbackQuery

from models.UserCl import UserCl

# Инициализация роутера
router = Router()

@router.callback_query(lambda c: c.data == "buy_vpn")
async def handle_buy_vpn(callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
    bot = callback_query.bot
    await callback_query.answer("Купить VPN: функционал пока реализован не до конца.")
    print('chat_id = ', chat_id)
    us = await UserCl.load_user(chat_id)
    print(await us.count_key.get())
    status = await us.servers[0].status_key.get()
    print(status)