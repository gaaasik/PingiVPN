from aiogram import Router
from aiogram.types import CallbackQuery







router = Router()


@router.callback_query(lambda c: c.data == "share")
async def handle_share(callback_query: CallbackQuery):
    await callback_query.answer("Пригласить: функционал пока не реализован.")
