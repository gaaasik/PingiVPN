
# bot/handlers/show_qr.py
from aiogram import Router, types
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