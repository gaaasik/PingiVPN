from aiogram import Router
from aiogram.types import CallbackQuery







router = Router()


@router.callback_query(lambda c: c.data == "help")
async def handle_help(callback_query: CallbackQuery):
    await callback_query.answer("Помощь: функционал пока не реализован.")